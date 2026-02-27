import json
import re
import typing

from fastapi.responses import StreamingResponse
import httpx
import os

from pathlib import Path
from typing import Annotated, Any

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from litserve.specs.openai import ChatCompletionRequest, TextContent
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.base.llms.types import ChatMessage, MessageRole, TextBlock
from llama_index.core.agent.workflow import AgentStream, FunctionAgent, ReActAgent, ToolCallResult, ToolCall, AgentOutput
from llama_index.core.workflow import Context, InputRequiredEvent, HumanResponseEvent
from qdrant_client.models import CreateFieldIndex
from workflows.events import StopEvent
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolOutput
from llama_index.core.node_parser import SentenceSplitter
from qdrant_client import AsyncQdrantClient, QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from tools import CalculatorTool, CreateFileTool, FindFileTool, ReadFileTool, RunTerminalCommandTool
from model import ConfirmToolCallRequest, ListFilesRequest, ListFilesResponse, ListFilesResponseItem, SetProjectInfoRequest
from config import DevAssistantConfig
from llama_index.core.storage.chat_store.base_db import MessageStatus
from llama_index.core.memory import (
    Memory,
    StaticMemoryBlock,
    FactExtractionMemoryBlock,
    VectorMemoryBlock,
    InsertMethod,
)
from llama_index.core.base.response.schema import Response
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.prompts import RichPromptTemplate
from llama_index.core.agent.react.output_parser import ReActOutputParser
from llama_index.core.agent.react.types import (
    ActionReasoningStep,
    BaseReasoningStep,
    ResponseReasoningStep,
)

class ReActOutputParser2(ReActOutputParser):
    def parse(self, output: str, is_streaming: bool = False) -> BaseReasoningStep:
        try:
            return super().parse(output, is_streaming)
        except ValueError as e:
            if 'Could not extract final answer' not in str(e):
                raise e
            answer = self._try_parse_answer_only(output)
            thought = "(Implicit) I can answer without any more tools!"
            return ResponseReasoningStep(
                thought=thought, response=answer, is_streaming=is_streaming
            )
            
    
    def _try_parse_answer_only(self, input_text: str) -> str:
        pattern = r"\s*Answer:(.*?)(?:$)"

        match = re.search(pattern, input_text, re.DOTALL)
        if not match:
            raise ValueError(
                f"Could not extract final answer from input text: {input_text}"
            )

        return match.group(1).strip()


class DevAssistantRag:
    def __init__(self, config: DevAssistantConfig):
        client = httpx.Client(proxy=config.proxy)
        aclient = httpx.AsyncClient(proxy=config.proxy)
        Settings.llm = OpenAILike(
            model='Coder LLM', api_base=config.api_base,
            is_chat_model=True, is_function_calling_model=True,
            http_client=client, async_http_client=aclient # type: ignore
        )
        Settings.embed_model = OpenAILikeEmbedding(
            model_name="Embedding Model", api_base=config.api_base,
            http_client=client, async_http_client=aclient
        )
        self.config = config
        self.engine = self._init_engine()

    def _init_engine(self):
        aclient = AsyncQdrantClient(url=self.config.qdrant_url)
        client = QdrantClient(url=self.config.qdrant_url)
        vector_store = QdrantVectorStore(client=client, aclient=aclient, collection_name='code')
        context = StorageContext.from_defaults(vector_store=vector_store)

        if client.collection_exists('code'):
            index = VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=context)
        else:
            files = [x.as_posix() for x in Path("data").rglob("*.cs")]
            reader = SimpleDirectoryReader(input_files=files)
            docs = reader.load_data()
            splitter = SentenceSplitter(chunk_size=128, chunk_overlap=0)
            index = VectorStoreIndex.from_documents(
                documents=docs, storage_context=context,
                transformations=[splitter], show_progress=True)        
        return index.as_query_engine(similarity_top_k=5)
    

class DevAssistantAgent:
    def __init__(self, rag: DevAssistantRag):
        self.rag = rag
        # mult = FunctionTool.from_defaults(self.calculator)
        # rag_tool = FunctionTool.from_defaults(self.search_codebase)
        rag_descr = """
Use query_engine_tool for:
- answer questions about source code behavior
- answer questions about source code description
- searching source code repository
Do NOT use this tool with files in working directory
Usage Cost: 50
"""
        rag_tool = QueryEngineTool.from_defaults(
            self.rag.engine,
            description=rag_descr
        )
        calc_tool = CalculatorTool()
        read_file = ReadFileTool()
        create_file = CreateFileTool()
        find_file = FindFileTool()
        run_terminal_cmd = RunTerminalCommandTool()
        # self.engine = index.as_chat_engine(streaming=True, similarity_top_k=2)
        # self.agent = FunctionAgent(
        #     tools=[mult, rag_tool],
        #     system_prompt="You are a helpful assistant that can perform calculations and search through documents to answer questions.",
        #     llm=Settings.llm
        # )
        self.agent = ReActAgent(tools=[calc_tool, rag_tool, read_file, create_file, find_file, run_terminal_cmd], verbose=True)
        self.agent.formatter = ReActChatFormatter.from_defaults(
            system_header=self._get_system_prompt(), observation_role=MessageRole.TOOL)
        self.agent.output_parser = ReActOutputParser2()
        self.work_dirs: dict[str, str] = dict()
        self.contexts: dict[str, Context] = dict()
        self.memory_slots: dict[str, Memory] = dict()

    def _get_system_prompt(self):
        with (Path(__file__).parents[0] / Path("system_prompt_template.md")).open("r") as f:
            prompt_str = f.read()
        return prompt_str.replace("{context_prompt}", "", 1)


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
            # VectorMemoryBlock(
            #     name="vector_memory",
            #     # required: pass in a vector store like qdrant, chroma, weaviate, milvus, etc.
            #     vector_store=vector_store,
            #     priority=2,
            #     embed_model=Settings.embed_model,
            #     # The top-k message batches to retrieve
            #     # similarity_top_k=2,
            #     # optional: How many previous messages to include in the retrieval query
            #     # retrieval_context_window=5
            #     # optional: pass optional node-postprocessors for things like similarity threshold, etc.
            #     # node_postprocessors=[...],
            # ),
        ]
        memory = Memory.from_defaults(
            session_id=session_id,
            token_limit=20000,
            memory_blocks=blocks,
            insert_method=InsertMethod.USER,
            # memory_blocks_template=MEMORY_BLOCKS_TEMPLATE
        )
        return memory
    
    async def search_codebase(self, ctx: Context, input: Annotated[str, 'What to find']):
        """Use it for searching the code base, answer questions about code behavior, and code description."""
        question = "Assistant wants to call the tool: search\nAre you sure you want to proceed?"
        response = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id=question,
            waiter_event=InputRequiredEvent(
                prefix=question, # type: ignore
            ),
        )
        if response.response:
            query_result = await self.rag.engine.aquery(input)
            return query_result.response # type: ignore
        else:
            return 'User declined tool calling. Please choose another tool or answer without using a tool.'
    
    def stream(self, request):
        if isinstance(request, ChatCompletionRequest):
            return self._stream_chat_message(request)
        elif isinstance(request, SetProjectInfoRequest):
            return self._set_project_info(request)
        elif isinstance(request, ConfirmToolCallRequest):
            return self._confirm_tool_call(request)
        elif isinstance(request, ListFilesRequest):
            return self._list_files(request)
        else:
            raise TypeError('Unsupported request type: ' + str(type(request)))
        
    async def _list_files(self, request: ListFilesRequest):
        if not request.path:
            request.path = '.'
        
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
                name += '/'
            path = str(item.relative_to(request.work_directory))
            path = path.replace('\\', '/')
            files.append(ListFilesResponseItem(name=name, path=path))

        yield ListFilesResponse(content=files)
        
    async def _confirm_tool_call(self, request: ConfirmToolCallRequest):
        if request.session_id in self.contexts:
            ctx = self.contexts[request.session_id]
            ctx.send_event(HumanResponseEvent(
                response=request.call_allowed, # type: ignore
                session_id=request.session_id # type: ignore
            ))
        if False: yield
        
    async def _set_project_info(self, request: SetProjectInfoRequest):
        self.work_dirs[request.session_id] = request.work_directory
        if not request.session_id in self.memory_slots:
            self.memory_slots[request.session_id] = self._create_memory(request.session_id, request.core_info)
        else:
            memory = self.memory_slots[request.session_id]
            info = request.core_info
            if request.os:
                info += f"\nTarget OS: {request.os}"
            memory.memory_blocks[0] = self._create_static_memory_block(info)
        if False: yield

    async def _process_message(self, ctx: Context | None, message):
        if not isinstance(message, str):
            raise NotImplementedError()
        if not ctx:
            return message
        work_dir = await ctx.store.get('work_dir', None)
        if not work_dir:
            return message
        files = re.findall(r'(?:^|\s)@([^\s]+)', message)
        token_count = 0
        message = re.sub(r'(?:^|\s)(@[^\s]+)', '', message)
        for path in files:
            full_path = os.path.join(work_dir, path)
            if not os.path.isfile(full_path):
                continue
            with open(full_path, 'rt') as f:
                content = f.read()
            tokens = Settings.tokenizer(content)
            token_count += len(tokens)
            if token_count > Settings.context_window // 2:
                break
            message = f"Content of file '{path}' provided by the User:\n```{content}\n```\n" + message
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
                await ctx.store.set('work_dir', self.work_dirs[request.user])
                await ctx.store.set('session_id', request.user)
        
        messages = [
            ChatMessage(content=await self._process_message(ctx, message.content), role=MessageRole(message.role))
            for message in request.messages
        ]

        memory = None
        history = None
        if request.user and request.user in self.memory_slots:
            memory = self.memory_slots[request.user]
        else:
            history = messages[:-1]

        handler = self.agent.run(messages[-1].content, ctx=ctx, memory=memory, chat_history=history)
        start_output = False
        last_event = None
        async for event in handler.stream_events():
            # print(type(event), event)
            # print()
            if isinstance(event, AgentStream):
                yield {"type": "reasoning", "role": "assistant", "content": event.delta}
            elif isinstance(event, ToolCall):
                yield {"type": "tool_call", "role": "assistant", "content": "", "tool_calls": [{"id": event.tool_id, "function": {"name": event.tool_name, "arguments": json.dumps(event.tool_kwargs)}, "type": "function"}]}
            elif isinstance(event, ToolCallResult):
                content = ''
                output = event.tool_output.raw_output
                if isinstance(output, Response):
                    content = output.response
                else:
                    content = str(output)
                yield {"type": "tool_call_result", "role": "tool", "content": content, "tool_calls": [{"id": event.tool_id, "function": {"name": event.tool_name, "arguments": json.dumps(event.tool_kwargs)}, "type": "function"}]}
            elif isinstance(event, StopEvent):
                content = ''
                if isinstance(event.result, AgentOutput):
                    content = event.result.response.content
                else:
                    content = str(event.result)
                yield {"type": "answer", "role": "assistant", "content": content}
            elif isinstance(event, InputRequiredEvent):
                yield {"type": "tool_call_confirm", "role": "tool", "content": event.prefix}
            # if isinstance(event, AgentStream):
            #     last_event = event
            #     if start_output:
            #         yield event.delta
            #     if event.response.strip().endswith("\nAnswer:"):
            #         start_output = True

        # if not start_output and last_event:
        #     yield last_event.response
