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

    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    test_db = SqliteDatabase(db_path)

    # Swap the proxy to SQLite for tests
    db.initialize(test_db)
    test_db.bind([User, Url, Event])
    test_db.connect(reuse_if_open=True)
    test_db.create_tables([User, Url, Event])

    application.config['TESTING'] = True
    yield application

    test_db.drop_tables([User, Url, Event])
    test_db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    from app.models.user import User
    return User.create(username='testuser', email='test@example.com')
