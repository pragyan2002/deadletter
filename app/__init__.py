import logging
from time import perf_counter

from dotenv import load_dotenv
from flask import Flask, g, got_request_exception

from app.database import db, init_db
from app.errors import register_error_handlers
from app.logging_config import configure_logging
from app.routes import register_routes


def create_app():
    load_dotenv()
    configure_logging()

    app = Flask(__name__)
    logger = logging.getLogger("app.request")

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee
    from app.models.event import Event
    from app.models.url import Url
    from app.models.user import User

    with db.connection_context():
        db.create_tables([User, Url, Event], safe=True)

    @app.before_request
    def start_request_timer():
        g.request_start_time = perf_counter()

    @app.after_request
    def log_request(response):
        start_time = getattr(g, "request_start_time", perf_counter())
        duration_ms = round((perf_counter() - start_time) * 1000, 2)
        g.request_duration_ms = duration_ms
        g.response_status_code = response.status_code
        logger.info("request_completed")
        return response

    @got_request_exception.connect_via(app)
    def log_unhandled_exception(sender, exception, **extra):
        logger.exception("request_exception", exc_info=exception)

    register_routes(app)
    register_error_handlers(app)

    return app
