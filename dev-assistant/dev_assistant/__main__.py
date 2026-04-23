import logging

import dotenv
from litserve import LitServer
from starlette.middleware.cors import CORSMiddleware

from .config import DevAssistantConfig
from .otel_logging import setup_otel_logging
from .server import LlamaIndexAPI, OpenAISpecModels

setup_otel_logging()
logger = logging.getLogger("dev-assistant")

logging.info("Starting dev assistant service")

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
server.run(port=8000, generate_client_file=False)
