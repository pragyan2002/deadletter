import os
import tempfile
from pathlib import Path

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


@pytest.fixture(scope='session')
def test_db_path():
    # Create a fresh file-backed SQLite database per full pytest run.
    db_fd, db_path = tempfile.mkstemp(prefix='deadletter-tests-', suffix='.db')
    os.close(db_fd)

    original_database_url = os.environ.get('DATABASE_URL')
    original_sqlite_path = os.environ.get('SQLITE_PATH')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['SQLITE_PATH'] = db_path

    try:
        yield db_path
    finally:
        if original_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = original_database_url

        if original_sqlite_path is None:
            os.environ.pop('SQLITE_PATH', None)
        else:
            os.environ['SQLITE_PATH'] = original_sqlite_path

        Path(db_path).unlink(missing_ok=True)


@pytest.fixture(scope='session')
def test_db(test_db_path):
    from app.database import db
    from app.models.event import Event
    from app.models.url import Url
    from app.models.user import User

    sqlite_db = SqliteDatabase(test_db_path)

    # Initialize and create schema at suite start against this run's temp DB.
    db.initialize(sqlite_db)
    sqlite_db.bind([User, Url, Event])
    sqlite_db.connect(reuse_if_open=True)
    sqlite_db.create_tables([User, Url, Event], safe=True)

    yield sqlite_db

    sqlite_db.drop_tables([User, Url, Event], safe=True)
    sqlite_db.close()


@pytest.fixture(autouse=True)
def clean_db(test_db):
    from app.models.event import Event
    from app.models.url import Url
    from app.models.user import User

    # Keep tests isolated while still using one per-run temporary DB file.
    test_db.drop_tables([User, Url, Event], safe=True)
    test_db.create_tables([User, Url, Event], safe=True)
    yield


@pytest.fixture
def app(test_db):
    from app import create_app

    application = create_app()
    application.config['TESTING'] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    from app.models.user import User
    return User.create(username='testuser', email='test@example.com')
