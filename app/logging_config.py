import logging

from flask import g, has_request_context, request
from pythonjsonlogger.json import JsonFormatter


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.method = None
        record.path = None
        record.status_code = None
        record.duration_ms = None
        record.request_id = None

        if has_request_context():
            record.method = request.method
            record.path = request.path
            record.request_id = request.headers.get("X-Request-ID")
            record.status_code = getattr(g, "response_status_code", None)
            record.duration_ms = getattr(g, "request_duration_ms", None)

        return True


def configure_logging():
    handler = logging.StreamHandler()
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(method)s %(path)s "
        "%(status_code)s %(duration_ms)s %(request_id)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
            "message": "message",
        },
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)
