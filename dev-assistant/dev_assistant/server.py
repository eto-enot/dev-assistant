import litserve as ls
import requests
import requests
import dotenv
import os

from banks import ChatMessage
from fastapi.responses import JSONResponse
from fastapi import Request, Response
from agent import DevAssistantAgent, DevAssistantConfig, DevAssistantRag
from starlette.middleware.cors import CORSMiddleware
import asyncio


class LlamaIndexAPI(ls.LitAPI):
    def __init__(self, config: DevAssistantConfig, **kwargs):
        super().__init__(**kwargs)
        self.config = config
    
    def setup(self, device):
        rag = DevAssistantRag(self.config)
        rag._init_engine()
        self.llm = DevAssistantAgent(rag)

    async def predict(self, x, **kwargs):
        async for token in self.llm.stream(x):
            yield token

    async def encode_response(self, output, **kwargs):
        async for out in output:
            yield ChatMessage(role='assistant', content=out)


class OpenAISpecModels(ls.OpenAISpec):
    def __init__(self, api_url):
        super().__init__()
        self.api_url = api_url

    def pre_setup(self, lit_api: ls.LitAPI):
        self.add_endpoint('/v1/models', self.models, ["GET"])
        self.add_endpoint('/v1/models', self.options_models, ["OPTIONS"])
        super().pre_setup(lit_api)

    async def models(self, request: Request):
        response = requests.get(self.api_url + '/models').json()
        return JSONResponse(response)
    
    async def options_models(self, request: Request):
        return Response(status_code=200)


if __name__ == "__main__":
    dotenv.load_dotenv()

    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    # logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

    config = DevAssistantConfig.from_env()
    
    middlewares=[
        (CORSMiddleware, {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_headers": ["*"],
            "allow_methods": ["DELETE", "GET", "POST", "PUT"]
        }),
    ]

    api = LlamaIndexAPI(config, spec=OpenAISpecModels(config.api_base), stream=True, enable_async=True)
    server = ls.LitServer(api, middlewares=middlewares)
    server.run(port=8000, generate_client_file=False)