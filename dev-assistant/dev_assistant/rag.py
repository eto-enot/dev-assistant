import logging
from pathlib import Path

from llama_index.core import (Settings, SimpleDirectoryReader, StorageContext,
                              VectorStoreIndex)
from llama_index.core.query_engine.retriever_query_engine import \
    RetrieverQueryEngine
from llama_index.postprocessor.jinaai_rerank import JinaRerank
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient, QdrantClient

try:
    from chunking import SourceCodeNodeParser
    from config import DevAssistantConfig
    from otel import setup_otel
except ImportError:
    from dev_assistant.chunking import SourceCodeNodeParser
    from dev_assistant.config import DevAssistantConfig
    from dev_assistant.otel import setup_otel


COLLECTION_NAME = "code"
setup_otel()
logger = logging.getLogger("dev-assistant.rag")


class DevAssistantRag:
    def __init__(self, config: DevAssistantConfig):
        self.config = config
        self.engine = None

    def init_engine(self):
        index = self.create_index("")
        retriever = index.as_retriever(similarity_top_k=self.config.rag_topk + 5)
        rerank = JinaRerank(
            top_n=self.config.rag_topk,
            model="Rerank Model",
            base_url=self.config.api_base,
            api_key="",
        )
        self.engine = RetrieverQueryEngine.from_args(
            retriever, llm=Settings.llm, node_postprocessors=[rerank]
        )

    def create_index(self, work_dir: str, filter: str = "*"):
        logger.info('Creating index for %s, filter %s', work_dir, filter)
        aclient = AsyncQdrantClient(url=self.config.qdrant_url)
        client = QdrantClient(url=self.config.qdrant_url)
        vector_store = QdrantVectorStore(
            client=client,
            aclient=aclient,
            collection_name=COLLECTION_NAME,
            enable_hybrid=True,
            fastembed_sparse_model="Qdrant/bm25",
        )
        context = StorageContext.from_defaults(vector_store=vector_store)

        if work_dir and client.collection_exists(COLLECTION_NAME):
            client.delete_collection(COLLECTION_NAME)

        if client.collection_exists(COLLECTION_NAME):
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, storage_context=context
            )
        elif work_dir:
            files = [x.as_posix() for x in Path(work_dir).rglob(filter)]
            reader = SimpleDirectoryReader(input_files=files)
            docs = reader.load_data()
            parser = SourceCodeNodeParser(chunk_size=self.config.rag_chunk_size)
            nodes = parser(docs)
            index = VectorStoreIndex(nodes, storage_context=context, show_progress=True)
        else:
            index = VectorStoreIndex([], storage_context=context)

        logger.info("Index created")

        return index
