from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient, QdrantClient

try:
    from chunking import SourceCodeNodeParser
    from config import DevAssistantConfig
except ImportError:
    from dev_assistant.chunking import SourceCodeNodeParser
    from dev_assistant.config import DevAssistantConfig


COLLECTION_NAME = "code"


class DevAssistantRag:
    def __init__(self, config: DevAssistantConfig):
        self.config = config
        self.engine = None

    def init_engine(self):
        index = self.create_index("data", )
        self.engine = index.as_query_engine(similarity_top_k=5)

    def create_index(self, work_dir: str, filter: str = "*"):
        aclient = AsyncQdrantClient(url=self.config.qdrant_url)
        client = QdrantClient(url=self.config.qdrant_url)
        vector_store = QdrantVectorStore(
            client=client, aclient=aclient, collection_name=COLLECTION_NAME
        )
        context = StorageContext.from_defaults(vector_store=vector_store)

        if client.collection_exists(COLLECTION_NAME):
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, storage_context=context
            )
        elif work_dir:
            files = [x.as_posix() for x in Path(work_dir).rglob(filter)]
            reader = SimpleDirectoryReader(input_files=files)
            docs = reader.load_data()
            # splitter = SentenceSplitter(chunk_size=128, chunk_overlap=0)
            parser = SourceCodeNodeParser(chunk_size=1024)
            nodes = parser(docs)
            index = VectorStoreIndex(nodes, storage_context=context, show_progress=True)
        else:
            index = VectorStoreIndex([], storage_context=context)

        return index
