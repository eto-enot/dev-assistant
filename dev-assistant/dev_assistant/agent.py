import json

import httpx
import os

from pathlib import Path
from typing import Annotated, Any

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from litserve.specs.openai import ChatCompletionRequest
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
from tools import CalculatorTool, CreateFileTool, FindFileTool, ReadFileTool
from model import ConfirmToolCallRequest, SetProjectInfoRequest
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


MEMORY_BLOCKS_TEMPLATE = RichPromptTemplate(
"""
Below are some basic facts provided by the User. Use them when making your answer, as needed.

{% for (block_name, block_content) in memory_blocks %}
<{{ block_name }}>
  {% for block in block_content %}
    {% if block.block_type == "text" %}
{{ block.text }}
    {% endif %}
  {% endfor %}
</{{ block_name }}>
{% endfor %}

---
"""
)


class DevAssistantConfig:
    API_BASE_URL_KEY = 'API_BASE_URL'
    QDRANT_URL_KEY = 'QDRANT_URL'
    PROXY_URL_KEY = 'PROXY_URL'
    
    def __init__(self, api_base: str, qdrant_url: str, proxy: str | None = None):
        self.api_base = api_base
        self.qdrant_url = qdrant_url
        self.proxy = proxy

    @staticmethod
    def from_env():
        if not DevAssistantConfig.API_BASE_URL_KEY in os.environ:
            raise ValueError('API base url not specified.')
        if not DevAssistantConfig.QDRANT_URL_KEY in os.environ:
            raise ValueError('Qdrant url not specified.')
        
        api_url = os.environ[DevAssistantConfig.API_BASE_URL_KEY]
        qdrant_url = os.environ[DevAssistantConfig.QDRANT_URL_KEY]
        proxy = os.environ.get(DevAssistantConfig.PROXY_URL_KEY)
        print(proxy)
        
        return DevAssistantConfig(api_url, qdrant_url, proxy)


class DevAssistantRag:
    def __init__(self, config: DevAssistantConfig):
        client = httpx.Client(proxy=config.proxy)
        aclient = httpx.AsyncClient(proxy=config.proxy)
        Settings.llm = OpenAILike(
            model='Coder LLM', api_base=config.api_base,
            is_chat_model=True, is_function_calling_model=True,
            http_client=client, async_http_client=aclient
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
        read_file = ReadFileTool()
        create_file = CreateFileTool()
        find_file = FindFileTool()
        # self.engine = index.as_chat_engine(streaming=True, similarity_top_k=2)
        # self.agent = FunctionAgent(
        #     tools=[mult, rag_tool],
        #     system_prompt="You are a helpful assistant that can perform calculations and search through documents to answer questions.",
        #     llm=Settings.llm
        # )
        self.agent = ReActAgent(tools=[CalculatorTool(), rag_tool, read_file, create_file, find_file], verbose=True)
        self.agent.formatter = ReActChatFormatter.from_defaults(
            system_header=self._get_system_prompt(), observation_role=MessageRole.TOOL)
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
    
    def calculator(self, expression: Annotated[str, 'Arithmetic expression']):
        """Useful for arithmetic calculations."""
        try:
            print(f'Calculator called: {expression}')
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    async def search_codebase(self, ctx: Context, input: Annotated[str, 'What to find']):
        """Use it for searching the code base, answer questions about code behavior, and code description."""
        question = "Assistant wants to call the tool: search\nAre you sure you want to proceed?"
        response = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id=question,
            waiter_event=InputRequiredEvent(
                prefix=question,
            ),
        )
        if response.response:
            response = await self.rag.engine.aquery(input)
            return response.response
        else:
            return 'User declined tool calling. Please choose another tool or answer without using a tool.'
    
    def stream(self, request: ChatCompletionRequest | SetProjectInfoRequest):
        if isinstance(request, ChatCompletionRequest):
            return self._stream_chat_message(request)
        elif isinstance(request, SetProjectInfoRequest):
            return self._set_project_info(request)
        elif isinstance(request, ConfirmToolCallRequest):
            return self._confirm_tool_call(request)
        
    async def _confirm_tool_call(self, request: ConfirmToolCallRequest):
        if request.session_id in self.contexts:
            ctx = self.contexts[request.session_id]
            ctx.send_event(HumanResponseEvent(
                response=request.call_allowed,
                session_id=request.session_id
            ))
        if False: yield
        
    async def _set_project_info(self, request: SetProjectInfoRequest):
        self.work_dirs[request.session_id] = request.work_directory
        if not request.session_id in self.memory_slots:
            self.memory_slots[request.session_id] = self._create_memory(request.session_id, request.core_info)
        else:
            memory = self.memory_slots[request.session_id]
            memory.memory_blocks[0] = self._create_static_memory_block(request.core_info)
        if False: yield

    async def _stream_chat_message(self, request: ChatCompletionRequest):
        messages = [
            ChatMessage(content=message.content, role=MessageRole(message.role))
            for message in request.messages
        ]

        memory = None
        history = None
        if request.user and request.user in self.memory_slots:
            memory = self.memory_slots[request.user]
        else:
            history = messages[:-1]

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
