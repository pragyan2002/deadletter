from flask import jsonify


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error='bad_request', detail=str(e.description)), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error='not_found', detail=str(e.description)), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify(error='conflict', detail=str(e.description)), 409

    @app.errorhandler(415)
    def unsupported_media_type(e):
        return jsonify(error='unsupported_media_type', detail=str(e.description)), 415

    @app.errorhandler(500)
    def internal_error(e):
        from app.alerting import record_500_error  # lazy import avoids circular dependency
        record_500_error()
        return jsonify(error='internal_error', detail='an unexpected error occurred'), 500
