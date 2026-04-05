import random
import string
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, redirect, request
from peewee import IntegrityError

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app.validators import validate_url_create, validate_url_update

urls_bp = Blueprint('urls', __name__)


def _generate_short_code():
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if not Url.select().where(Url.short_code == code).exists():
            return code


def _url_dict(url):
    return {
        'short_code': url.short_code,
        'original_url': url.original_url,
        'title': url.title,
        'is_active': url.is_active,
        'user_id': url.user_id,
        'created_at': url.created_at.isoformat(),
        'updated_at': url.updated_at.isoformat(),
    }


@urls_bp.route('/urls', methods=['POST'])
def create_url():
    data = request.get_json(silent=True) or {}
    errors = validate_url_create(data)
    if errors:
        abort(400, description=errors[0])

    user = User.get_or_none(User.id == data['user_id'])
    if user is None:
        abort(404, description=f"user {data['user_id']} not found")

    short_code = _generate_short_code()

    try:
        with db.atomic():
            url = Url.create(
                user=user,
                short_code=short_code,
                original_url=data['original_url'].strip(),
                title=data['title'].strip(),
            )
            Event.create(
                url=url,
                user=user,
                event_type='created',
                details={'short_code': short_code, 'original_url': url.original_url},
            )
    except IntegrityError:
        abort(409, description=f'short_code {short_code} already exists')

    return jsonify(_url_dict(url)), 201


@urls_bp.route('/urls')
def list_urls():
    query = Url.select()

    user_id = request.args.get('user_id', type=int)
    if user_id is not None:
        query = query.where(Url.user == user_id)

    active = request.args.get('is_active')
    if active == 'true':
        query = query.where(Url.is_active == True)
    elif active == 'false':
        query = query.where(Url.is_active == False)

    return jsonify([_url_dict(u) for u in query.order_by(Url.created_at.desc())])


@urls_bp.route('/urls/<short_code>')
def get_url(short_code):
    url = Url.get_or_none(Url.short_code == short_code)
    if url is None:
        abort(404, description=f'short_code {short_code} not found')

    events = [
        {
            'id': e.id,
            'event_type': e.event_type,
            'timestamp': e.timestamp.isoformat(),
            'details': e.details,
            'user_id': e.user_id,
        }
        for e in Event.select().where(Event.url == url).order_by(Event.timestamp)
    ]

    result = _url_dict(url)
    result['events'] = events
    return jsonify(result)


@urls_bp.route('/urls/<short_code>', methods=['PUT'])
def update_url(short_code):
    url = Url.get_or_none(Url.short_code == short_code)
    if url is None:
        abort(404, description=f'short_code {short_code} not found')
    if not url.is_active:
        abort(404, description=f'short_code {short_code} is inactive')

    data = request.get_json(silent=True) or {}
    errors = validate_url_update(data)
    if errors:
        abort(400, description=errors[0])

    user = User.get_or_none(User.id == url.user_id)

    with db.atomic():
        if 'original_url' in data:
            new_url = data['original_url'].strip()
            Event.create(
                url=url,
                user=user,
                event_type='updated',
                details={'field': 'original_url', 'new_value': new_url},
            )
            url.original_url = new_url

        if 'title' in data:
            url.title = data['title'].strip()

        url.updated_at = datetime.now(timezone.utc)
        url.save()

    return jsonify(_url_dict(url))


@urls_bp.route('/urls/<short_code>', methods=['DELETE'])
def delete_url(short_code):
    url = Url.get_or_none(Url.short_code == short_code)
    if url is None:
        abort(404, description=f'short_code {short_code} not found')
    if not url.is_active:
        abort(409, description=f'short_code {short_code} is already inactive')

    data = request.get_json(silent=True) or {}
    reason = data.get('reason', 'user_requested')

    user = User.get_or_none(User.id == url.user_id)

    with db.atomic():
        url.is_active = False
        url.updated_at = datetime.now(timezone.utc)
        url.save()
        Event.create(
            url=url,
            user=user,
            event_type='deleted',
            details={'reason': reason},
        )

    return jsonify(_url_dict(url))


@urls_bp.route('/r/<short_code>')
def redirect_url(short_code):
    url = Url.get_or_none(Url.short_code == short_code)
    if url is None:
        abort(404, description=f'short_code {short_code} not found')
    if not url.is_active:
        abort(404, description=f'short_code {short_code} is inactive')
    return redirect(url.original_url, code=302)
