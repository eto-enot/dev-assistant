import logging

import dotenv
from litserve import LitServer
from starlette.middleware.cors import CORSMiddleware

from .config import DevAssistantConfig
from .otel import setup_otel
from .server import LlamaIndexAPI, OpenAISpecModels
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

setup_otel()
logger = logging.getLogger("dev-assistant")

logger.info("Starting dev assistant service")

dotenv.load_dotenv()
config = DevAssistantConfig.from_env()

middlewares = [
    (
        CORSMiddleware,
        {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_headers": ["*"],
            "allow_methods": ["DELETE", "GET", "POST", "PUT"],
        },
    ),
]

api = LlamaIndexAPI(
    config, spec=OpenAISpecModels(config.api_base), stream=True, enable_async=True
)
server = LitServer(api, middlewares=middlewares)  # type: ignore
FastAPIInstrumentor.instrument_app(server.app)

server.run(port=8000, generate_client_file=False)
