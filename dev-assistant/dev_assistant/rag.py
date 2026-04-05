import httpx

from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from qdrant_client import AsyncQdrantClient, QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

try:
    from chunking import SourceCodeNodeParser
    from config import DevAssistantConfig
except ImportError:
    from dev_assistant.chunking import SourceCodeNodeParser
    from dev_assistant.config import DevAssistantConfig

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
            #splitter = SentenceSplitter(chunk_size=128, chunk_overlap=0)
            parser = SourceCodeNodeParser(chunk_size=1024)
            nodes = parser(docs)
            index = VectorStoreIndex(nodes, storage_context=context, show_progress=True)
            # index = VectorStoreIndex.from_documents(
            #     documents=docs, storage_context=context,
            #     transformations=[splitter], show_progress=True)        
        return index.as_query_engine(similarity_top_k=5)