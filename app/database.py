import os
import urllib.parse

from peewee import DatabaseProxy, Model, PostgresqlDatabase, SqliteDatabase

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("sqlite:///"):
        sqlite_path = database_url.replace("sqlite:///", "", 1)
        database = SqliteDatabase(sqlite_path)
    elif database_url:
        parsed = urllib.parse.urlparse(database_url)
        database = PostgresqlDatabase(
            parsed.path.lstrip('/'),
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
        )
    elif os.environ.get("DATABASE_ENGINE", "").lower() == "postgres":
        database = PostgresqlDatabase(
            os.environ.get("DATABASE_NAME", "hackathon_db"),
            host=os.environ.get("DATABASE_HOST", "localhost"),
            port=int(os.environ.get("DATABASE_PORT", 5432)),
            user=os.environ.get("DATABASE_USER", "postgres"),
            password=os.environ.get("DATABASE_PASSWORD", "postgres"),
        )
    else:
        database = SqliteDatabase(os.environ.get("SQLITE_PATH", "deadletter.db"))
    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()
