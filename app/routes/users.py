from flask import Blueprint, abort, jsonify, request

from app.models.url import Url
from app.models.user import User
from app.validators import validate_user_create

users_bp = Blueprint('users', __name__)


@users_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json(silent=True) or {}
    errors = validate_user_create(data)
    if errors:
        abort(400, description=errors[0])

    user = User.create(
        username=data['username'].strip(),
        email=data['email'].strip(),
    )
    return jsonify(id=user.id, username=user.username, email=user.email,
                   created_at=user.created_at.isoformat()), 201


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
