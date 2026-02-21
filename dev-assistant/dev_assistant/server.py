import asyncio
from collections import deque
import time
import uuid

import litserve as ls
from litserve.callbacks.base import EventTypes
from pydantic import BaseModel
import requests
import requests
import dotenv

from banks import ChatMessage
from fastapi.responses import JSONResponse
from fastapi import Request, Response
from agent import DevAssistantAgent, DevAssistantConfig, DevAssistantRag
from starlette.middleware.cors import CORSMiddleware
from litserve.utils import ResponseBufferItem
from model import SetProjectInfoRequest


class LlamaIndexAPI(ls.LitAPI):
    def __init__(self, config: DevAssistantConfig, **kwargs):
        super().__init__(**kwargs)
        self.config = config
    
    def setup(self, device):
        rag = DevAssistantRag(self.config)
        self.agent = DevAssistantAgent(rag)
        pass

    async def predict(self, x, **kwargs):
        async for token in self.agent.stream(x):
            yield token

    async def encode_response(self, output, **kwargs):
        async for out in output:
            yield ChatMessage(role='assistant', content=out)


class OpenAISpecModels(ls.OpenAISpec):
    def __init__(self, api_url):
        super().__init__()
        self.api_url = api_url
        self.work_dirs = dict()
        self.work_dir_updated = None

    def pre_setup(self, lit_api: ls.LitAPI):
        self.add_endpoint('/v1/models', self.models, ["GET"])
        self.add_endpoint('/v1/models', self.options_models, ["OPTIONS"])
        self.add_endpoint('/set-project-info', self.set_project_info, ["POST"])
        super().pre_setup(lit_api)

    async def models(self, request: Request):
        response = requests.get(self.api_url + '/models').json()
        return JSONResponse(response)
    
    async def options_models(self, request: Request):
        return Response(status_code=200)
    
    def populate_context(self, context, request):
        if isinstance(request, SetProjectInfoRequest):
            return
        super().populate_context(context, request)
        
    
    async def set_project_info(self, request: SetProjectInfoRequest):
        self._server._callback_runner.trigger_event(
            EventTypes.ON_REQUEST.value,
            active_requests=self._server.active_requests,
            litserver=self._server,
        )

        self._put_request_to_queue(request)        
        return Response(status_code=200)
    
    def _put_request_to_queue(self, request: BaseModel):
        request_el = request.model_copy()
        uid = uuid.uuid4()
        self.response_buffer[uid] = ResponseBufferItem(asyncio.Event(), deque())
        self.request_queue.put((self.response_queue_id, uid, time.monotonic(), request_el))


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