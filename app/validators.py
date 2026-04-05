VALID_EVENT_TYPES = {'created', 'updated', 'deleted'}
VALID_DELETE_REASONS = {'policy_cleanup', 'user_requested', 'duplicate'}


def validate_url_create(data):
    """Validate POST /urls request body. Returns list of error strings."""
    errors = []

    original_url = data.get('original_url', '').strip()
    if not original_url:
        errors.append('original_url is required')
    elif not (original_url.startswith('http://') or original_url.startswith('https://')):
        errors.append('original_url must start with http:// or https://')

    title = data.get('title', '').strip()
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

    if 'original_url' not in data and 'title' not in data:
        errors.append('at least one of original_url or title is required')

    if 'original_url' in data:
        original_url = data['original_url'].strip()
        if not (original_url.startswith('http://') or original_url.startswith('https://')):
            errors.append('original_url must start with http:// or https://')

    return errors


def validate_user_create(data):
    """Validate POST /users request body. Returns list of error strings."""
    errors = []

    if not data.get('username', '').strip():
        errors.append('username is required')

    if not data.get('email', '').strip():
        errors.append('email is required')

    return errors
