from werkzeug.exceptions import BadRequest


def parse_json_object(request, *, require_json=True):
    if require_json and not request.is_json:
        raise ValueError('Content-Type must be application/json')

    try:
        data = request.get_json(silent=False)
    except BadRequest as exc:
        raise ValueError('request body must be valid JSON') from exc

    if data is None:
        raise ValueError('request body must be valid JSON')
    if not isinstance(data, dict):
        raise ValueError('request body must be an object')
    return data
