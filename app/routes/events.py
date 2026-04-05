from flask import Blueprint, jsonify, request

from app.models.event import Event
from app.models.url import Url

events_bp = Blueprint('events', __name__)


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

    return jsonify([
        {
            'id': e.id,
            'url_id': e.url_id,
            'user_id': e.user_id,
            'event_type': e.event_type,
            'timestamp': e.timestamp.isoformat(),
            'details': e.details,
        }
        for e in query.order_by(Event.timestamp.desc())
    ])
