import json
import logging
import os
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated

from litserve.specs.openai import ChatCompletionRequest
from llama_index.core import Settings
from llama_index.core.agent.workflow import (AgentOutput, AgentStream,
                                             FunctionAgent, ToolCall,
                                             ToolCallResult)
from llama_index.core.base.llms.types import (ChatMessage, MessageRole,
                                              TextBlock)
from llama_index.core.base.response.schema import Response
from llama_index.core.memory import (FactExtractionMemoryBlock, InsertMethod,
                                     Memory, StaticMemoryBlock)
from llama_index.core.tools import QueryEngineTool
from llama_index.core.workflow import (Context, HumanResponseEvent,
                                       InputRequiredEvent)
from workflows.events import StopEvent

from .otel import setup_otel
from .celery_tasks import reindex_project_task
from .model import (ConfirmToolCallRequest, ListFilesRequest,
                    ListFilesResponse, ListFilesResponseItem,
                    ReindexProjectRequest, ReindexProjectResponse,
                    SetProjectInfoRequest)
from .rag import DevAssistantRag
from .tools import (CalculatorTool, CreateFileTool, EditFileTool, FindFileTool,
                    ReadFileTool, RunTerminalCommandTool)

setup_otel()
logger = logging.getLogger("dev-assistant")

RAG_TOOL_DESCRIPTION = """This is a query tool to a RAG system built on the user organization's \
source code repositories. The purpose of this tool is to:
- answer questions about source code behavior.
- answer questions about source code description.
- searching source code repository.
Do NOT use this tool with files in working directory. Do NOT call this tool unless the user's \
question relates to the aspects listed above.
Usage Cost: 100
"""


class DevAssistantAgent:
    def __init__(self, rag: DevAssistantRag):
        logger.debug("Initializing dev assistant agent")
        self.rag = rag

        tools = [
            CalculatorTool(),
            ReadFileTool(),
            CreateFileTool(),
            FindFileTool(),
            RunTerminalCommandTool(),
            EditFileTool(),
            QueryEngineTool.from_defaults(
                self.rag.engine, description=RAG_TOOL_DESCRIPTION
            ),
        ]

        self.agent = FunctionAgent(
            tools=tools, system_prompt=self._get_system_prompt(), verbose=True
        )

        self.work_dirs: dict[str, str] = dict()
        self.contexts: dict[str, Context] = dict()
        self.memory_slots: dict[str, Memory] = dict()

    def _get_system_prompt(self):
        with (Path(__file__).parents[0] / Path("system_prompt_template.md")).open(
            "r"
        ) as f:
            prompt_str = f.read()
        return prompt_str.format(
            os=platform.platform(), datetime=datetime.today().strftime("%Y-%m-%d")
        )

    def _create_static_memory_block(self, core_info: str):
        return StaticMemoryBlock(
            name="core_info",
            static_content=[TextBlock(text=core_info)],
            priority=0,
        )

    def _create_memory(self, session_id: str, core_info: str):
        blocks = [
            self._create_static_memory_block(core_info),
            FactExtractionMemoryBlock(
                name="extracted_info",
                llm=Settings.llm,
                max_facts=50,
                priority=1,
            ),
        ]
        memory = Memory.from_defaults(
            session_id=session_id,
            token_limit=20000,
            memory_blocks=blocks,
            insert_method=InsertMethod.USER,
            # memory_blocks_template=MEMORY_BLOCKS_TEMPLATE
        )
        return memory

    async def search_codebase(
        self, ctx: Context, input: Annotated[str, "What to find"]
    ):
        """Use it for searching the code base, answer questions about \
        code behavior, and code description."""

        question = "Assistant wants to call the tool: search\nAre you sure you want to proceed?"
        response = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id=question,
            waiter_event=InputRequiredEvent(
                prefix=question,  # type: ignore
            ),
        )

        if response.response:
            query_result = await self.rag.engine.aquery(input)
            return query_result.response  # type: ignore
        else:
            return "User declined tool calling. Please choose another tool or answer without using a tool."

    def stream(self, request):
        if isinstance(request, ChatCompletionRequest):
            return self._stream_chat_message(request)
        elif isinstance(request, SetProjectInfoRequest):
            return self._set_project_info(request)
        elif isinstance(request, ConfirmToolCallRequest):
            return self._confirm_tool_call(request)
        elif isinstance(request, ListFilesRequest):
            return self._list_files(request)
        elif isinstance(request, ReindexProjectRequest):
            return self._reindex_project(request)
        else:
            raise TypeError("Unsupported request type: " + str(type(request)))

    async def _list_files(self, request: ListFilesRequest):
        if not request.path:
            request.path = "."

        abs_path = (Path(request.work_directory) / Path(request.path)).resolve()

        if not abs_path.exists() or not abs_path.is_dir():
            yield ListFilesResponse(content=[])
            return

        files = []
        for item in abs_path.iterdir():
            name = item.name
            if request.filter.upper() not in name.upper():
                continue
            if item.is_dir():
                name += "/"
            path = str(item.relative_to(request.work_directory))
            path = path.replace("\\", "/")
            files.append(ListFilesResponseItem(name=name, path=path))

        yield ListFilesResponse(content=files)

    async def _reindex_project(self, request: ReindexProjectRequest):
        reindex_project_task.delay(request.work_directory)  # type: ignore
        yield ReindexProjectResponse()

    async def _confirm_tool_call(self, request: ConfirmToolCallRequest):
        if request.session_id in self.contexts:
            ctx = self.contexts[request.session_id]
            ctx.send_event(
                HumanResponseEvent(
                    response=request.call_allowed,  # type: ignore
                    session_id=request.session_id,  # type: ignore
                )
            )
        if False:
            yield

    async def _set_project_info(self, request: SetProjectInfoRequest):
        self.work_dirs[request.session_id] = request.work_directory
        if request.session_id not in self.memory_slots:
            self.memory_slots[request.session_id] = self._create_memory(
                request.session_id, request.core_info
            )
        else:
            memory = self.memory_slots[request.session_id]
            info = request.core_info
            if request.os:
                info += f"\nTarget OS: {request.os}"
            memory.memory_blocks[0] = self._create_static_memory_block(info)
        if False:
            yield

    async def _process_message(self, ctx: Context | None, message):
        if not isinstance(message, str):
            raise NotImplementedError()
        if not ctx:
            return message
        work_dir = await ctx.store.get("work_dir", None)
        if not work_dir:
            return message
        files = re.findall(r"(?:^|\s)@([^\s]+)", message)
        token_count = 0
        message = re.sub(r"(?:^|\s)(@[^\s]+)", "", message)
        for path in files:
            full_path = os.path.join(work_dir, path)
            if not os.path.isfile(full_path):
                continue
            with open(full_path, "rt", encoding="utf-8") as f:
                content = f.read()
            tokens = Settings.tokenizer(content)
            token_count += len(tokens)
            if token_count > Settings.context_window // 2:
                break
            message = (
                f"Content of file '{path}' provided by the User:\n```{content}\n```\n"
                + message
            )
        return message

    async def _stream_chat_message(self, request: ChatCompletionRequest):
        ctx = None
        if request.user:
            if request.user in self.contexts:
                ctx = self.contexts[request.user]
            else:
                ctx = Context(self.agent)
                self.contexts[request.user] = ctx
            if request.user in self.work_dirs:
                await ctx.store.set("work_dir", self.work_dirs[request.user])
                await ctx.store.set("session_id", request.user)

        messages = [
            ChatMessage(
                content=await self._process_message(ctx, message.content),
                role=MessageRole(message.role),
            )
            for message in request.messages
        ]

        memory = None
        history = None
        if request.user and request.user in self.memory_slots:
            memory = self.memory_slots[request.user]
        else:
            history = messages[:-1]

        handler = self.agent.run(
            messages[-1].content, ctx=ctx, memory=memory, chat_history=history
        )

        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                yield {
                    "type": "reasoning",
                    "role": MessageRole.ASSISTANT,
                    "content": event.delta,
                }
            elif isinstance(event, ToolCall):
                yield {
                    "type": "tool_call",
                    "role": MessageRole.ASSISTANT,
                    "content": "",
                    "tool_calls": [
                        {
                            "id": event.tool_id,
                            "function": {
                                "name": event.tool_name,
                                "arguments": json.dumps(event.tool_kwargs),
                            },
                            "type": "function",
                        }
                    ],
                }
            elif isinstance(event, ToolCallResult):
                content = ""
                output = event.tool_output.raw_output
                if isinstance(output, Response):
                    content = output.response
                else:
                    content = str(output)
                yield {
                    "type": "tool_call_result",
                    "role": MessageRole.TOOL,
                    "content": content,
                    "tool_calls": [
                        {
                            "id": event.tool_id,
                            "function": {
                                "name": event.tool_name,
                                "arguments": json.dumps(event.tool_kwargs),
                            },
                            "type": "function",
                        }
                    ],
                }
            elif isinstance(event, StopEvent):
                content = ""
                if isinstance(event.result, AgentOutput):
                    content = event.result.response.content
                else:
                    content = str(event.result)
                yield {"type": "answer", "role": "assistant", "content": content}
            elif isinstance(event, InputRequiredEvent):
                yield {
                    "type": "tool_call_confirm",
                    "role": MessageRole.TOOL,
                    "content": event.prefix,
                }
