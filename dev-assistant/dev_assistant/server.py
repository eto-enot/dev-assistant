import asyncio
from collections import deque
from collections.abc import Iterator
import json
from pathlib import Path
import time
import uuid

from litserve import LitServer, LitAPI, OpenAISpec
from litserve.specs.openai import ChatCompletionChunk, ChatCompletionStreamingChoice, ChatMessage, ChatMessageWithUsage, ChatCompletionRequest, ChoiceDelta, UsageInfo, _openai_format_error
from litserve.utils import LitAPIStatus, ResponseBufferItem, azip
from litserve.callbacks.base import EventTypes
from pydantic import BaseModel
import requests
import requests
import dotenv

from fastapi.responses import JSONResponse
from fastapi import HTTPException, Request, Response
from agent import DevAssistantAgent, DevAssistantRag
from config import DevAssistantConfig
from starlette.middleware.cors import CORSMiddleware
from litserve.utils import ResponseBufferItem
from model import ConfirmToolCallRequest, ListFilesResponse, ListFilesResponseItem, SetProjectInfoRequest, ListFilesRequest, ChatCompletionChunkType
import logging

logger = logging.getLogger(__name__)


class LlamaIndexAPI(LitAPI):
    def __init__(self, config: DevAssistantConfig, **kwargs):
        super().__init__(**kwargs)
        self.config = config
    
    def setup(self, device):
        rag = DevAssistantRag(self.config)
        self.agent = DevAssistantAgent(rag)
        pass

    async def predict(self, x, **kwargs):
        # if isinstance(x, ListFilesRequest):
        #     yield self._list_files(x)
        async for token in self.agent.stream(x):
            yield token

    # async def encode_response(self, output, **kwargs):
    #     async for out in output:
    #         yield ChatMessage(role=out['role'], content=out['content'])

    # def _list_files(self, request: ListFilesRequest):
    #     if not request.path:
    #         request.path = '.'
        
    #     abs_path = (Path(request.work_directory) / Path(request.path)).resolve()
        
    #     if not abs_path.exists() or not abs_path.is_dir():
    #         return []
        
    #     files = []
    #     for item in abs_path.iterdir():
    #         name = item.name
    #         if request.filter.upper() not in name.upper():
    #             continue
    #         if item.is_dir():
    #             name += '/'
    #         path = str(item.relative_to(request.work_directory))
    #         path = path.replace('\\', '/')
    #         files.append(ListFilesResponseItem(name=name, path=path))

    #     return files


class OpenAISpecModels(OpenAISpec):
    def __init__(self, api_url):
        super().__init__()
        self.api_url = api_url
        self.work_dirs = dict()
        self.work_dir_updated = None

    def pre_setup(self, lit_api: LitAPI):
        self.add_endpoint('/v1/models', self.models, ["GET"])
        self.add_endpoint('/v1/models', self.options_models, ["OPTIONS"])
        self.add_endpoint('/set-project-info', self._set_project_info, ["POST"])
        self.add_endpoint('/confirm-tool-call', self._confirm_tool_call, ["POST"])
        self.add_endpoint('/list-files', self._list_files, ["POST"])
        super().pre_setup(lit_api)

    async def models(self, request: Request):
        response = requests.get(self.api_url + '/models').json()
        return JSONResponse(response)
    
    async def options_models(self, request: Request):
        return Response(status_code=200)
    
    def populate_context(self, context, request):
        ignore = (SetProjectInfoRequest, ConfirmToolCallRequest, ListFilesRequest)
        if isinstance(request, ignore):
            return
        super().populate_context(context, request)

    async def streaming_completion(self, request: ChatCompletionRequest, pipe_responses: list):
        try:
            model = request.model
            usage_info = None
            type = ""
            async for streaming_response in azip(*pipe_responses):
                choices = []
                usage_infos = []
                # iterate over n choices
                for i, (response, status) in enumerate(streaming_response):
                    if status == LitAPIStatus.ERROR and isinstance(response, HTTPException):
                        raise response
                    elif status == LitAPIStatus.ERROR:
                        logger.error("Error in streaming response: %s", response)
                        raise HTTPException(status_code=500)
                    encoded_response = json.loads(response)
                    logger.debug(encoded_response)
                    type = encoded_response["type"]
                    chat_msg = ChoiceDelta(**encoded_response)
                    usage_infos.append(UsageInfo(**encoded_response))
                    choice = ChatCompletionStreamingChoice(
                        index=i, delta=chat_msg, finish_reason=None
                    )

                    choices.append(choice)

                # Only use the last item from encode_response
                usage_info = sum(usage_infos)
                chunk = ChatCompletionChunkType(model=model, choices=choices, usage=None, type=type)
                logger.debug(chunk)
                yield f"data: {chunk.model_dump_json(by_alias=True)}\n\n"

            choices = [
                ChatCompletionStreamingChoice(
                    index=i,
                    delta=ChoiceDelta(),
                    finish_reason="stop",
                )
                for i in range(request.n)
            ]
            last_chunk = ChatCompletionChunkType(
                model=model,
                choices=choices,
                usage=usage_info,
                type=type
            )
            yield f"data: {last_chunk.model_dump_json(by_alias=True)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Error in streaming response: %s", e, exc_info=True)
            yield _openai_format_error(e)
            return
        
    def _encode_response(self, output):
        if isinstance(output, list) and len(output) and isinstance(output[0], ListFilesResponseItem):
            return output
        return super()._encode_response(output)
        
    async def _set_project_info(self, request: SetProjectInfoRequest):
        self._put_request_to_queue(request)
        return Response(status_code=200)
    
    async def _confirm_tool_call(self, request: ConfirmToolCallRequest):
        self._put_request_to_queue(request)
        return Response(status_code=200)

    async def _list_files(self, request: ListFilesRequest):
        uid, event, queue = self._put_request_to_queue(request)
        data = self.data_streamer(queue, event, send_status=True)
        async for response, status in data:
            if status == LitAPIStatus.ERROR and isinstance(response, HTTPException):
                raise response
            elif status == LitAPIStatus.ERROR:
                raise HTTPException(status_code=500)
            
            return Response(ListFilesResponse.dump_json(response), status_code=200)
    
    def _put_request_to_queue(self, request: BaseModel):
        self._server._callback_runner.trigger_event(
            EventTypes.ON_REQUEST.value,
            active_requests=self._server.active_requests,
            litserver=self._server,
        )

        event = asyncio.Event()
        queue = deque()
        request_el = request.model_copy()
        uid = uuid.uuid4()
        self.response_buffer[uid] = ResponseBufferItem(event, queue)
        self.request_queue.put((self.response_queue_id, uid, time.monotonic(), request_el))

        return uid, event, queue


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
    server = LitServer(api, middlewares=middlewares)
    server.run(port=8000, generate_client_file=False)