import os
import tempfile

import pytest
from peewee import SqliteDatabase
from playhouse.sqlite_ext import JSONField

# Patch BinaryJSONField before any app model imports.
# BinaryJSONField emits Postgres-specific DDL (USING jsonb / GIN indexes)
# that SQLite cannot parse. Replacing it with SQLite's JSONField in the
# postgres_ext module means that when event.py does
# `from playhouse.postgres_ext import BinaryJSONField` it gets JSONField.
import playhouse.postgres_ext as _pg_ext
_pg_ext.BinaryJSONField = JSONField

# Use a file-based SQLite DB for tests (not :memory:) so that the connection
# can be closed and reopened between requests without losing data. The Flask
# teardown_appcontext hook closes the DB after every request; :memory: would
# give a fresh empty database on the next reconnect, breaking multi-request tests.
_db_fd, _db_path = tempfile.mkstemp(suffix='.db')
os.close(_db_fd)
TEST_DB = SqliteDatabase(_db_path)

os.environ.setdefault('DATABASE_NAME', 'test')
os.environ.setdefault('DATABASE_HOST', 'localhost')
os.environ.setdefault('DATABASE_USER', 'postgres')
os.environ.setdefault('DATABASE_PASSWORD', 'postgres')


@pytest.fixture
def app():
    from app import create_app
    from app.database import db
    from app.models.user import User
    from app.models.url import Url
    from app.models.event import Event

    application = create_app()

    # Swap the proxy to SQLite for tests
    db.initialize(TEST_DB)
    TEST_DB.bind([User, Url, Event])
    TEST_DB.connect(reuse_if_open=True)
    TEST_DB.create_tables([User, Url, Event])

    application.config['TESTING'] = True
    yield application

    TEST_DB.drop_tables([User, Url, Event])
    TEST_DB.close()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    from app.models.user import User
    return User.create(username='testuser', email='test@example.com')
