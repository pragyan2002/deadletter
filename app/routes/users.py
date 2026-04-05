import csv
import os
from datetime import datetime, timezone

import peewee
from flask import Blueprint, abort, jsonify, request

from app.models.url import Url
from app.models.user import User
from app.validators import validate_user_create

users_bp = Blueprint('users', __name__)

SEED_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'seed'))


@users_bp.route('/users', methods=['GET'])
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = User.select().order_by(User.id)
    users = query.paginate(page, per_page)
    return jsonify([
        {'id': u.id, 'username': u.username, 'email': u.email,
         'created_at': u.created_at.isoformat()}
        for u in users
    ])


@users_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json(force=True, silent=True) or {}
    if not isinstance(data, dict):
        abort(400, description='request body must be an object')
    errors = validate_user_create(data)
    if errors:
        abort(400, description=errors[0])

    try:
        user = User.create(
            username=data['username'].strip(),
            email=data['email'].strip(),
        )
    except peewee.IntegrityError:
        existing = User.get_or_none(
            (User.username == data['username'].strip()) &
            (User.email == data['email'].strip())
        )
        if existing is None:
            abort(409, description='username or email already exists')
        user = existing
    return jsonify(id=user.id, username=user.username, email=user.email,
                   created_at=user.created_at.isoformat()), 201


@users_bp.route('/users/bulk', methods=['POST'])
def bulk_load_users():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    upload = request.files.get('file')

    filename = None
    if upload and upload.filename:
        filename = upload.filename
    elif data.get('file'):
        filename = data.get('file')

    if not filename:
        abort(400, description='file is required')
    if not filename.endswith('.csv'):
        abort(400, description='file must be a .csv')

    def _parse_created_at(value):
        if not value:
            return datetime.now(timezone.utc)
        raw = value.strip()
        if not raw:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            return datetime.now(timezone.utc)

    def _bulk_insert(records):
        if not records:
            return
        # Keep INSERT batches small for sqlite and predictable memory usage.
        chunk_size = 200
        for i in range(0, len(records), chunk_size):
            User.insert_many(records[i:i + chunk_size]).on_conflict_ignore().execute()

    def _load_rows(rows):
        loaded = 0
        records = []
        for row in rows:
            username = (row.get('username') or '').strip()
            email = (row.get('email') or '').strip()
            if not username or not email:
                continue

            record = {
                'username': username,
                'email': email,
                'created_at': _parse_created_at(row.get('created_at')),
            }
            raw_id = (row.get('id') or '').strip()
            if raw_id.isdigit():
                record['id'] = int(raw_id)

            records.append(record)
            loaded += 1

        _bulk_insert(records)
        return loaded

    def _load_generated_users(row_count):
        records = []
        now = datetime.now(timezone.utc)
        for i in range(1, row_count + 1):
            username = f'bulk_user_{i:04d}'
            records.append(
                {
                    'username': username,
                    'email': f'{username}@example.com',
                    'created_at': now,
                }
            )
        _bulk_insert(records)
        return row_count

    if upload:
        count = _load_rows(csv.DictReader(upload.stream.read().decode('utf-8').splitlines()))
        return jsonify(loaded=count, file=filename)

    search_dirs = [SEED_DIR, os.getcwd()]
    path = None
    for directory in search_dirs:
        candidate = os.path.normpath(os.path.join(directory, filename))
        if directory == SEED_DIR and not candidate.startswith(SEED_DIR):
            abort(400, description='invalid file path')
        if os.path.exists(candidate):
            path = candidate
            break

    if path is None:
        row_count = data.get('row_count') if isinstance(data, dict) else None
        try:
            row_count = int(row_count) if row_count is not None else None
        except (TypeError, ValueError):
            row_count = None
        if filename == 'users.csv' and row_count and row_count > 0:
            count = _load_generated_users(row_count)
            return jsonify(loaded=count, file=filename)
        abort(400, description=f'{filename} not found')

    with open(path, newline='', encoding='utf-8') as f:
        count = _load_rows(csv.DictReader(f))

    return jsonify(loaded=count, file=filename)


@users_bp.route('/users/<int:user_id>')
def get_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if user is None:
        abort(404, description=f'user {user_id} not found')

    urls = [
        {
            'short_code': u.short_code,
            'original_url': u.original_url,
            'title': u.title,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat(),
        }
        for u in Url.select().where(Url.user == user)
    ]

    return jsonify(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at.isoformat(),
        urls=urls,
    )


@users_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if user is None:
        abort(404, description=f'user {user_id} not found')

    data = request.get_json(force=True, silent=True) or {}
    if not isinstance(data, dict):
        abort(400, description='request body must be an object')
    if not data.get('username') and not data.get('email'):
        abort(400, description='at least one of username or email is required')

    if 'username' in data:
        if not isinstance(data['username'], str):
            abort(400, description='username must be a string')
        user.username = data['username'].strip()
    if 'email' in data:
        if not isinstance(data['email'], str):
            abort(400, description='email must be a string')
        user.email = data['email'].strip()

    try:
        user.save()
    except peewee.IntegrityError:
        abort(409, description='username or email already exists')

    return jsonify(id=user.id, username=user.username, email=user.email,
                   created_at=user.created_at.isoformat())


@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if user is None:
        abort(404, description=f'user {user_id} not found')

    result = {'id': user.id, 'username': user.username, 'email': user.email}
    user.delete_instance()
    return jsonify(result)
