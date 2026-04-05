from werkzeug.exceptions import BadRequest


def parse_json_object(
    request,
    *,
    require_json=True,
    allow_empty_body=False,
    allow_null_as_empty_object=False,
):
    raw_body = request.get_data(cache=True, as_text=False) or b""
    if allow_empty_body and len(raw_body) == 0:
        return {}

    if require_json and not request.is_json:
        raise ValueError('Content-Type must be application/json')

    try:
        data = request.get_json(silent=False)
    except BadRequest as exc:
        raise ValueError('request body must be valid JSON') from exc

    if data is None:
        if allow_null_as_empty_object:
            return {}
        raise ValueError('request body must be valid JSON')
    if not isinstance(data, dict):
        raise ValueError('request body must be an object')
    return data
