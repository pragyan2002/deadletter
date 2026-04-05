from flask import Blueprint, jsonify

from app.database import db

health_bp = Blueprint('health', __name__)


def _check_database():
    db.connect(reuse_if_open=True)
    db.execute_sql("SELECT 1")


@health_bp.route('/health')
def health():
    try:
        _check_database()
    except Exception as exc:  # health endpoint must never crash
        return jsonify(status='degraded', detail=f'database unavailable: {exc.__class__.__name__}'), 503

    return jsonify(status='ok')
