import csv
import json
import os
from datetime import datetime

from flask import Blueprint, abort, jsonify, request

from app.models.event import Event
from app.models.url import Url

events_bp = Blueprint('events', __name__)

SEED_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'seed'))


@events_bp.route('/events')
def list_events():
    query = Event.select()

    url_id = request.args.get('url_id', type=int)
    if url_id is not None:
        query = query.where(Event.url == url_id)

    short_code = request.args.get('short_code')
    if short_code is not None:
        url = Url.get_or_none(Url.short_code == short_code)
        if url:
            query = query.where(Event.url == url)

    event_type = request.args.get('event_type')
    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    query = query.order_by(Event.timestamp.desc())

    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', type=int)
    if page is not None and per_page is not None:
        query = query.paginate(page, per_page)

    return jsonify([
        {
            'id': e.id,
            'url_id': e.url_id,
            'user_id': e.user_id,
            'event_type': e.event_type,
            'timestamp': e.timestamp.isoformat(),
            'details': e.details,
        }
        for e in query
    ])


@events_bp.route('/events/bulk', methods=['POST'])
def bulk_load_events():
    data = request.get_json(force=True, silent=True) or {}
    filename = data.get('file')
    if not filename:
        abort(400, description='file is required')
    if not filename.endswith('.csv'):
        abort(400, description='file must be a .csv')

    path = os.path.normpath(os.path.join(SEED_DIR, filename))
    if not path.startswith(SEED_DIR):
        abort(400, description='invalid file path')
    if not os.path.exists(path):
        abort(400, description=f'{filename} not found')

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

    return jsonify(loaded=count, file=filename)
