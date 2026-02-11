import httpx
import os

from pathlib import Path
from typing import Annotated

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext, load_index_from_storage
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from litserve.specs.openai import ChatCompletionRequest
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.agent.workflow import FunctionAgent, AgentStream, ReActAgent, ToolCallResult
from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.node_parser import SentenceSplitter
from qdrant_client import AsyncQdrantClient, QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from traitlets import Instance


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
        Settings.llm = OpenAILike(
            model='Coder LLM', api_base=config.api_base,
            is_chat_model=True, is_function_calling_model=True,
            http_client=client
        )
        Settings.embed_model = OpenAILikeEmbedding(
            model_name="Embedding Model", api_base=config.api_base,
            http_client=client
        )
        self.config = config
        self.engine = None

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
        self.engine = index.as_query_engine(similarity_top_k=5)
    

class DevAssistantAgent:
    def __init__(self, rag: DevAssistantRag):
        self.rag = rag
        mult = FunctionTool.from_defaults(self.multiply)
        rag_tool = QueryEngineTool.from_defaults(
            self.rag.engine, 'search',
            'Useful for answering natural language questions about to find something or where something is located.'
        )
        # self.engine = index.as_chat_engine(streaming=True, similarity_top_k=2)
        # self.agent = FunctionAgent(
        #     tools=[mult, rag],
        #     system_prompt="You are a helpful assistant that can perform calculations and search through documents to answer questions.",
        #     llm=Settings.llm
        # )
        self.agent = ReActAgent(tools=[mult, rag_tool], verbose=True)


    def multiply(self, a: Annotated[float, 'First multiplier'], b: Annotated[float, 'Second multiplier']) -> float:
        """ Useful for multiplying two numbers."""
        print(f'multiply called: {a}, {b}')
        return a * b
    
    async def search(self, query: Annotated[str, 'What to find']) -> str:
        """ Useful for answering natural language questions about to find something."""
        print(f'search called: {query}')
        response = await self.rag.engine.aquery(query)
        return str(response)

    async def stream(self, messages_dict: ChatCompletionRequest):
        messages = [
            ChatMessage(content=message.content, role=MessageRole(message.role))
            for message in messages_dict.messages
        ]

        handler = self.agent.run(messages[-1].content, chat_history=messages[:-1])
        start_output = False
        last_event = None
        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                yield event.delta
            elif isinstance(event, ToolCallResult):
                yield '\n'
            # if isinstance(event, AgentStream):
            #     last_event = event
            #     if start_output:
            #         yield event.delta
            #     if event.response.strip().endswith("\nAnswer:"):
            #         start_output = True

        if not start_output and last_event:
            yield last_event.response
