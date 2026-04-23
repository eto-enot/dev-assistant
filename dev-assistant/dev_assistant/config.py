import os

import httpx
from llama_index.core import Settings
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


class DevAssistantConfig:
    API_BASE_URL_KEY = "API_BASE_URL"
    QDRANT_URL_KEY = "QDRANT_URL"
    PROXY_URL_KEY = "PROXY_URL"
    RAG_TOP_K = "RAG_TOP_K"
    RAG_CHUNK_SIZE = "RAG_CHUNK_SIZE"

    def __init__(self, **kwargs):
        self.proxy = None
        self.api_base = ''
        self.qdrant_url = ''
        self.rag_topk = 10
        self.rag_chunk_size = 256
        self.__dict__.update(kwargs)

    def init_models(self):
        client = httpx.Client(proxy=self.proxy)
        aclient = httpx.AsyncClient(proxy=self.proxy)

        HTTPXClientInstrumentor.instrument_client(client)
        HTTPXClientInstrumentor.instrument_client(aclient)

        Settings.llm = OpenAILike(
            model="Coder LLM",
            api_base=self.api_base,
            is_chat_model=True,
            is_function_calling_model=True,
            http_client=client,  # type: ignore
            async_http_client=aclient,  # type: ignore
        )

        Settings.embed_model = OpenAILikeEmbedding(
            model_name="Embedding Model",
            api_base=self.api_base,
            http_client=client,
            async_http_client=aclient,
        )

    @staticmethod
    def from_env():
        if DevAssistantConfig.API_BASE_URL_KEY not in os.environ:
            raise ValueError("API base url not specified.")
        if DevAssistantConfig.QDRANT_URL_KEY not in os.environ:
            raise ValueError("Qdrant url not specified.")

        api_url = os.environ[DevAssistantConfig.API_BASE_URL_KEY]
        qdrant_url = os.environ[DevAssistantConfig.QDRANT_URL_KEY]
        proxy = os.environ.get(DevAssistantConfig.PROXY_URL_KEY)
        rag_topk = int(os.environ.get(DevAssistantConfig.RAG_TOP_K, 10))
        rag_chunk_size = int(os.environ.get(DevAssistantConfig.RAG_CHUNK_SIZE, 256))

        if proxy:
            os.environ['HTTP_PROXY'] = proxy
            os.environ['HTTPS_PROXY'] = proxy

        return DevAssistantConfig(
            api_base=api_url,
            qdrant_url=qdrant_url,
            proxy=proxy,
            rag_topk=rag_topk,
            rag_chunk_size=rag_chunk_size,
        )
