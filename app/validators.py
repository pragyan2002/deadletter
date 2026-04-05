VALID_EVENT_TYPES = {'created', 'updated', 'deleted'}
VALID_DELETE_REASONS = {'policy_cleanup', 'user_requested', 'duplicate'}


def validate_url_create(data):
    """Validate POST /urls request body. Returns list of error strings."""
    errors = []

    original_url_value = data.get('original_url', '')
    if not isinstance(original_url_value, str):
        errors.append('original_url must be a string')
        original_url = ''
    else:
        original_url = original_url_value.strip()

    if not original_url:
        errors.append('original_url is required')
    elif not (original_url.startswith('http://') or original_url.startswith('https://')):
        errors.append('original_url must start with http:// or https://')

    title_value = data.get('title', '')
    if not isinstance(title_value, str):
        errors.append('title must be a string')
        title = ''
    else:
        title = title_value.strip()

    if not title:
        errors.append('title is required')

    user_id = data.get('user_id')
    if user_id is None:
        errors.append('user_id is required')
    elif not isinstance(user_id, int) or user_id < 1:
        errors.append('user_id must be a positive integer')

    return errors


def validate_url_update(data):
    """Validate PUT /urls/<code> request body. Returns list of error strings."""
    errors = []

    if 'original_url' not in data and 'title' not in data and 'is_active' not in data:
        errors.append('at least one of original_url, title, or is_active is required')

    if 'original_url' in data:
        original_url_value = data['original_url']
        if not isinstance(original_url_value, str):
            errors.append('original_url must be a string')
        else:
            original_url = original_url_value.strip()
            if not (original_url.startswith('http://') or original_url.startswith('https://')):
                errors.append('original_url must start with http:// or https://')

    if 'title' in data:
        title_value = data['title']
        if not isinstance(title_value, str):
            errors.append('title must be a string')
        elif not title_value.strip():
            errors.append('title is required')

    if 'is_active' in data:
        is_active_value = data['is_active']
        if not isinstance(is_active_value, bool):
            errors.append('is_active must be a boolean')

    return errors


def validate_user_create(data):
    """Validate POST /users request body. Returns list of error strings."""
    errors = []

    username_value = data.get('username', '')
    if not isinstance(username_value, str):
        errors.append('username must be a string')
        username = ''
    else:
        username = username_value.strip()

    if not username:
        errors.append('username is required')

    email_value = data.get('email', '')
    if not isinstance(email_value, str):
        errors.append('email must be a string')
        email = ''
    else:
        email = email_value.strip()

    if not email:
        errors.append('email is required')

    return errors


def validate_event_type(value):
    """Validate event_type query parameter. Returns list of error strings."""
    errors = []

    if not isinstance(value, str):
        errors.append('event_type must be a string')
    elif value not in VALID_EVENT_TYPES:
        errors.append('event_type must be one of created, updated, deleted')

    return errors


def validate_delete_reason(data):
    """Validate DELETE /urls/<code> request body reason field. Returns list of error strings."""
    errors = []

    reason_value = data.get('reason', 'user_requested')
    if not isinstance(reason_value, str):
        errors.append('reason must be a string')
    elif reason_value not in VALID_DELETE_REASONS:
        errors.append('reason must be one of policy_cleanup, user_requested, duplicate')

    return errors
