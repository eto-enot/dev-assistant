import asyncio
import json
import logging
import time
import uuid
from collections import deque

import requests
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from litserve import LitAPI, OpenAISpec
from litserve.callbacks.base import EventTypes
from litserve.specs.openai import (ChatCompletionRequest,
                                   ChatCompletionStreamingChoice, ChoiceDelta,
                                   UsageInfo, _openai_format_error)
from litserve.utils import LitAPIStatus, ResponseBufferItem, azip
from pydantic import BaseModel

from .agent import DevAssistantAgent, DevAssistantRag
from .config import DevAssistantConfig
from .model import (ChatCompletionChunkType, ConfirmToolCallRequest,
                    ListFilesRequest, ListFilesResponse, ReindexProjectRequest,
                    ReindexProjectResponse, SetProjectInfoRequest)

logger = logging.getLogger("dev-assistant")


class LlamaIndexAPI(LitAPI):
    def __init__(self, config: DevAssistantConfig, **kwargs):
        super().__init__(**kwargs)
        self.config = config

    def setup(self, device):
        self.config.init_models()
        rag = DevAssistantRag(self.config)
        rag.init_engine()
        self.agent = DevAssistantAgent(rag)
        pass

    async def predict(self, x, **kwargs):
        async for token in self.agent.stream(x):
            yield token


class OpenAISpecModels(OpenAISpec):
    def __init__(self, api_url):
        super().__init__()
        self.api_url = api_url
        self.work_dirs = dict()
        self.work_dir_updated = None

    def pre_setup(self, lit_api: LitAPI):
        self.add_endpoint("/v1/models", self.models, ["GET"])
        self.add_endpoint("/v1/models", self.options_models, ["OPTIONS"])
        self.add_endpoint("/set-project-info", self._set_project_info, ["POST"])
        self.add_endpoint("/confirm-tool-call", self._confirm_tool_call, ["POST"])
        self.add_endpoint("/list-files", self._list_files, ["POST"])
        self.add_endpoint("/reindex", self._reindex_project, ["POST"])
        super().pre_setup(lit_api)

    async def models(self, request: Request):
        response = requests.get(self.api_url + "/models").json()
        return JSONResponse(response)

    async def options_models(self, request: Request):
        return Response(status_code=200)

    def populate_context(self, context, request):
        ignore = (
            SetProjectInfoRequest,
            ConfirmToolCallRequest,
            ListFilesRequest,
            ReindexProjectRequest,
        )
        if not isinstance(request, ignore):
            super().populate_context(context, request)

    async def streaming_completion(
        self, request: ChatCompletionRequest, pipe_responses: list
    ):
        try:
            model = request.model or ""
            usage_info = None
            type = ""
            async for streaming_response in azip(*pipe_responses):
                choices = []
                usage_infos = []
                for i, (response, status) in enumerate(streaming_response):
                    if status == LitAPIStatus.ERROR and isinstance(
                        response, HTTPException
                    ):
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

                usage_info = sum(usage_infos)
                chunk = ChatCompletionChunkType(
                    model=model, choices=choices, usage=None, type=type
                )
                logger.debug(chunk)
                yield f"data: {chunk.model_dump_json(by_alias=True)}\n\n"

            choices = [
                ChatCompletionStreamingChoice(
                    index=i,
                    delta=ChoiceDelta(),
                    finish_reason="stop",
                )
                for i in range(request.n or 0)
            ]
            last_chunk = ChatCompletionChunkType(
                model=model, choices=choices, usage=usage_info, type=type
            )
            yield f"data: {last_chunk.model_dump_json(by_alias=True)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Error in streaming response: %s", e, exc_info=True)
            yield _openai_format_error(e)
            return

    def _encode_response(self, output):
        ignore = (ListFilesResponse, ReindexProjectResponse)
        if isinstance(output, ignore):
            return output
        return super()._encode_response(output)

    async def _set_project_info(self, request: SetProjectInfoRequest):
        self._put_request_to_queue(request)
        return Response(status_code=200)

    async def _confirm_tool_call(self, request: ConfirmToolCallRequest):
        self._put_request_to_queue(request)
        return Response(status_code=200)

    async def _list_files(self, request: ListFilesRequest):
        _, event, queue = self._put_request_to_queue(request)
        data = self.data_streamer(queue, event, send_status=True)
        async for response, status in data:
            if status == LitAPIStatus.ERROR and isinstance(response, HTTPException):
                raise response
            elif status == LitAPIStatus.ERROR:
                raise HTTPException(status_code=500)
            return Response(response, status_code=200)

    async def _reindex_project(self, request: ReindexProjectRequest):
        _, event, queue = self._put_request_to_queue(request)
        data = self.data_streamer(queue, event, send_status=True)
        async for response, status in data:
            if status == LitAPIStatus.ERROR and isinstance(response, HTTPException):
                raise response
            elif status == LitAPIStatus.ERROR:
                raise HTTPException(status_code=500)
            return Response(response, status_code=200)

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
        assert self.response_buffer
        assert self.request_queue
        self.response_buffer[uid] = ResponseBufferItem(event, queue)  # type: ignore
        self.request_queue.put(
            (self.response_queue_id, uid, time.monotonic(), request_el)
        )

        return uid, event, queue
