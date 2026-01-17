import httpx
import os

from pathlib import Path
from typing import Annotated

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext, load_index_from_storage
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from litserve.specs.openai import ChatCompletionRequest
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.agent.workflow import FunctionAgent, AgentStream, ReActAgent
from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.node_parser import SentenceSplitter


class DevAssistantRag:
    def __init__(self, api_base):
        client = httpx.Client(proxy="http://localhost:8888")
        Settings.llm = OpenAILike(model='Coder LLM', api_base=api_base, is_chat_model=True, is_function_calling_model=True, http_client=client)
        Settings.embed_model = OpenAILikeEmbedding(model_name="Embedding Model", api_base=api_base, http_client=client)
        self.engine = self._get_index().as_query_engine(similarity_top_k=2)

    def _get_index(self):
        if os.path.isdir('context'):
            docstore = SimpleDocumentStore.from_persist_dir('context')
            vector_store = SimpleVectorStore.from_persist_dir('context')
            index_store = SimpleIndexStore.from_persist_dir('context')
            storage_context = StorageContext.from_defaults(
                docstore=docstore,
                vector_store=vector_store,
                index_store=index_store,
            )
            index = load_index_from_storage(storage_context)
        else:
            files = [x.as_posix() for x in Path("data").rglob("*.cs")]
            reader = SimpleDirectoryReader(input_files=files)
            docs = reader.load_data()
            storage_context = StorageContext.from_defaults(
                docstore=SimpleDocumentStore(),
                vector_store=SimpleVectorStore(),
                index_store=SimpleIndexStore(),
            )
            splitter = SentenceSplitter(
                chunk_size=128, chunk_overlap=0)
            index = VectorStoreIndex.from_documents(docs, storage_context, transformations=[splitter], show_progress=True)
            storage_context.persist('context')
        
        return index


class DevAssistantAgent:
    def __init__(self, api_base):
        self.rag = DevAssistantRag(api_base)
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
                last_event = event
                if start_output:
                    yield event.delta
                if (event.response.strip().endswith("\nAnswer:")):
                    start_output = True

        if not start_output and last_event:
            yield last_event.response
