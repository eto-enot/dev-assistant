import os
import sys
import logging

import opentelemetry.sdk.resources as res
import opentelemetry.sdk.environment_variables as ev
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

def setup_otel_logging():
    if any(filter(lambda x: isinstance(x, LoggingHandler), logging.getLogger().handlers)):
        return
    
    service_name = os.environ.get(ev.OTEL_SERVICE_NAME, 'dev-assistant')
    
    logger_provider = LoggerProvider(
        resource=res.Resource.create({
            res.SERVICE_NAME: service_name,
        }),
    )

    set_logger_provider(logger_provider)
    
    exporter = OTLPLogExporter(insecure=True)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

    logging.getLogger().setLevel(logging.NOTSET)
    logging.getLogger().addHandler(handler)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
