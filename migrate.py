"""
Run this script to create tables and optionally load seed data.

Usage:
    uv run migrate.py              # create tables only
    uv run migrate.py --seed       # create tables + load seed CSVs
"""
import csv
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from app.database import db, init_db
from flask import Flask

# Bootstrap a minimal app context so init_db can run
_app = Flask(__name__)
init_db(_app)

from app.models.user import User
from app.models.url import Url
from app.models.event import Event

SEED_DIR = os.path.join(os.path.dirname(__file__), 'seed')


def create_tables():
    with db.connection_context():
        db.create_tables([User, Url, Event], safe=True)
    print('Tables created (safe=True -- no-op if already exist).')


def load_seeds():
    with db.connection_context():
        _load_users()
        _load_urls()
        _load_events()
    print('Seed data loaded.')


def _load_users():
    path = os.path.join(SEED_DIR, 'users.csv')
    if not os.path.exists(path):
        print(f'  Skipping users: {path} not found')
        return
    count = 0
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            User.get_or_create(
                id=int(row['id']),
                defaults={
                    'username': row['username'],
                    'email': row['email'],
                    'created_at': datetime.fromisoformat(row['created_at']),
                },
            )
            count += 1
    print(f'  Users: {count} rows processed')


def _load_urls():
    path = os.path.join(SEED_DIR, 'urls.csv')
    if not os.path.exists(path):
        print(f'  Skipping urls: {path} not found')
        return
    count = 0
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            Url.get_or_create(
                id=int(row['id']),
                defaults={
                    'user_id': int(row['user_id']),
                    'short_code': row['short_code'],
                    'original_url': row['original_url'],
                    'title': row['title'],
                    'is_active': row['is_active'].lower() == 'true',
                    'created_at': datetime.fromisoformat(row['created_at']),
                    'updated_at': datetime.fromisoformat(row['updated_at']),
                },
            )
            count += 1
    print(f'  URLs: {count} rows processed')


def _load_events():
    import json
    path = os.path.join(SEED_DIR, 'events.csv')
    if not os.path.exists(path):
        print(f'  Skipping events: {path} not found')
        return
    count = 0
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            Event.get_or_create(
                id=int(row['id']),
                defaults={
                    'url_id': int(row['url_id']),
                    'user_id': int(row['user_id']),
                    'event_type': row['event_type'],
                    'timestamp': datetime.fromisoformat(row['timestamp']),
                    'details': json.loads(row['details']),
                },
            )
            count += 1
    print(f'  Events: {count} rows processed')


if __name__ == '__main__':
    create_tables()
    if '--seed' in sys.argv:
        load_seeds()
