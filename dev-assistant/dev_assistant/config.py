import os

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
        
        return DevAssistantConfig(api_url, qdrant_url, proxy)
