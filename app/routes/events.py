import csv
import json
import os
from datetime import datetime

from flask import Blueprint, abort, jsonify, request

from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app.validators import validate_event_type

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
        else:
            return jsonify([])

    event_type = request.args.get('event_type')
    if event_type is not None:
        errors = validate_event_type(event_type)
        if errors:
            abort(400, description=errors[0])
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


@events_bp.route('/events', methods=['POST'])
def create_event():
    data = request.get_json(force=True, silent=True) or {}
    if not isinstance(data, dict):
        abort(400, description='request body must be an object')

    url_id = data.get('url_id')
    if not isinstance(url_id, int) or url_id < 1:
        abort(400, description='url_id must be a positive integer')

    user_id = data.get('user_id')
    if not isinstance(user_id, int) or user_id < 1:
        abort(400, description='user_id must be a positive integer')

    event_type = data.get('event_type')
    if not isinstance(event_type, str) or not event_type.strip():
        abort(400, description='event_type is required')
    event_type = event_type.strip()
    # Keep POST /events aligned with canonical validator enum, including redirected.
    event_errors = validate_event_type(event_type)
    if event_errors:
        abort(400, description=event_errors[0])

    details = data.get('details', {})
    if not isinstance(details, dict):
        abort(400, description='details must be an object')

    url = Url.get_or_none(Url.id == url_id)
    if url is None:
        abort(404, description=f'url {url_id} not found')

    user = User.get_or_none(User.id == user_id)
    if user is None:
        abort(404, description=f'user {user_id} not found')

    event = Event.create(
        url=url,
        user=user,
        event_type=event_type,
        details=details,
    )

    return jsonify(
        id=event.id,
        url_id=event.url_id,
        user_id=event.user_id,
        event_type=event.event_type,
        timestamp=event.timestamp.isoformat(),
        details=event.details,
    ), 201


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
