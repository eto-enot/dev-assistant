import logging
import os
import sys

import opentelemetry.sdk.environment_variables as ev
import opentelemetry.sdk.resources as res
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import set_tracer_provider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


def setup_otel():
    if any(
        filter(lambda x: isinstance(x, LoggingHandler), logging.getLogger().handlers)
    ):
        return

    service_name = os.environ.get(ev.OTEL_SERVICE_NAME, "dev-assistant")
    resource = res.Resource.create(
        {
            res.SERVICE_NAME: service_name,
        }
    )

    logger_provider = LoggerProvider(resource=resource)
    trace_provider = TracerProvider(resource=resource)

    set_logger_provider(logger_provider)
    set_tracer_provider(trace_provider)

    log_exporter = OTLPLogExporter(insecure=True)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))

    trace_exporter = OTLPSpanExporter(insecure=True)
    trace_provider.add_span_processor(SimpleSpanProcessor(trace_exporter))

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

    logging.getLogger().addHandler(handler)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.getLogger().setLevel(logging.NOTSET)
