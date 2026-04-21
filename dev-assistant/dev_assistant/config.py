import os

import httpx
from llama_index.core import Settings
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike


class DevAssistantConfig:
    API_BASE_URL_KEY = "API_BASE_URL"
    QDRANT_URL_KEY = "QDRANT_URL"
    PROXY_URL_KEY = "PROXY_URL"

    def __init__(self, api_base: str, qdrant_url: str, proxy: str | None = None):
        self.api_base = api_base
        self.qdrant_url = qdrant_url
        self.proxy = proxy

    def init_models(self):
        client = httpx.Client(proxy=self.proxy)
        aclient = httpx.AsyncClient(proxy=self.proxy)

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

        return DevAssistantConfig(api_url, qdrant_url, proxy)
