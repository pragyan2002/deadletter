VALID_EVENT_TYPES = {'created', 'updated', 'deleted'}
VALID_DELETE_REASONS = {'policy_cleanup', 'user_requested', 'duplicate'}


def _require_non_empty_string(data, field, errors):
    value = data.get(field)
    if not isinstance(value, str):
        errors.append(f'{field} must be a string')
        return None
    stripped = value.strip()
    if not stripped:
        errors.append(f'{field} is required')
        return None
    return stripped


def validate_url_create(data):
    """Validate POST /urls request body. Returns list of error strings."""
    errors = []

    original_url = _require_non_empty_string(data, 'original_url', errors)
    if original_url and not (original_url.startswith('http://') or original_url.startswith('https://')):
        errors.append('original_url must start with http:// or https://')

    _require_non_empty_string(data, 'title', errors)

    user_id = data.get('user_id')
    if user_id is None:
        errors.append('user_id is required')
    elif not isinstance(user_id, int) or user_id < 1:
        errors.append('user_id must be a positive integer')

    return errors


def validate_url_update(data):
    """Validate PUT /urls/<code> request body. Returns list of error strings."""
    errors = []

    if 'original_url' not in data and 'title' not in data:
        errors.append('at least one of original_url or title is required')

    if 'original_url' in data:
        if not isinstance(data['original_url'], str):
            errors.append('original_url must be a string')
        else:
            original_url = data['original_url'].strip()
            if not (original_url.startswith('http://') or original_url.startswith('https://')):
                errors.append('original_url must start with http:// or https://')

    if 'title' in data:
        if not isinstance(data['title'], str):
            errors.append('title must be a string')
        elif not data['title'].strip():
            errors.append('title is required')

    return errors


def validate_delete_reason(data):
    """Validate DELETE /urls/<code> request body reason. Returns list of error strings."""
    errors = []

    reason = data.get('reason', 'user_requested')
    if not isinstance(reason, str):
        errors.append('reason must be a string')
    elif reason not in VALID_DELETE_REASONS:
        errors.append(
            f"reason must be one of: {', '.join(sorted(VALID_DELETE_REASONS))}"
        )

    return errors


def validate_user_create(data):
    """Validate POST /users request body. Returns list of error strings."""
    errors = []

    _require_non_empty_string(data, 'username', errors)
    _require_non_empty_string(data, 'email', errors)

    return errors
