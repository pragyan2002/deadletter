from app.validators import (
    validate_delete_reason,
    validate_event_type,
    validate_url_create,
    validate_url_update,
    validate_user_create,
)


class TestValidateUrlCreate:
    def test_valid(self):
        assert validate_url_create({'original_url': 'https://example.com', 'title': 'Test', 'user_id': 1}) == []

    def test_missing_url(self):
        errors = validate_url_create({'title': 'Test', 'user_id': 1})
        assert any('original_url' in e for e in errors)

    def test_bad_scheme(self):
        errors = validate_url_create({'original_url': 'ftp://example.com', 'title': 'Test', 'user_id': 1})
        assert any('http' in e for e in errors)

    def test_missing_title(self):
        errors = validate_url_create({'original_url': 'https://example.com', 'user_id': 1})
        assert any('title' in e for e in errors)

    def test_missing_user_id(self):
        errors = validate_url_create({'original_url': 'https://example.com', 'title': 'Test'})
        assert any('user_id' in e for e in errors)

    def test_http_scheme_ok(self):
        assert validate_url_create({'original_url': 'http://example.com', 'title': 'Test', 'user_id': 1}) == []

    def test_original_url_non_string(self):
        errors = validate_url_create({'original_url': 123, 'title': 'Test', 'user_id': 1})
        assert 'original_url must be a string' in errors

    def test_title_non_string(self):
        errors = validate_url_create({'original_url': 'https://example.com', 'title': ['bad'], 'user_id': 1})
        assert 'title must be a string' in errors


class TestValidateUrlUpdate:
    def test_valid_url(self):
        assert validate_url_update({'original_url': 'https://new.example.com'}) == []

    def test_valid_title(self):
        assert validate_url_update({'title': 'New title'}) == []

    def test_empty_body(self):
        errors = validate_url_update({})
        assert errors

    def test_bad_scheme(self):
        errors = validate_url_update({'original_url': 'ftp://bad.com'})
        assert errors

    def test_original_url_non_string(self):
        errors = validate_url_update({'original_url': 999})
        assert 'original_url must be a string' in errors

    def test_title_non_string(self):
        errors = validate_url_update({'title': {'bad': 'type'}})
        assert 'title must be a string' in errors

    def test_title_whitespace_only(self):
        errors = validate_url_update({'title': '   '})
        assert 'title is required' in errors

    def test_valid_is_active_boolean(self):
        assert validate_url_update({'is_active': False}) == []

    def test_invalid_is_active_non_boolean(self):
        errors = validate_url_update({'is_active': 'false'})
        assert 'is_active must be a boolean' in errors


class TestValidateUserCreate:
    def test_valid(self):
        assert validate_user_create({'username': 'alice', 'email': 'alice@example.com'}) == []

    def test_missing_username(self):
        errors = validate_user_create({'email': 'alice@example.com'})
        assert any('username' in e for e in errors)

    def test_missing_email(self):
        errors = validate_user_create({'username': 'alice'})
        assert any('email' in e for e in errors)

    def test_username_non_string(self):
        errors = validate_user_create({'username': 99, 'email': 'alice@example.com'})
        assert 'username must be a string' in errors

    def test_email_non_string(self):
        errors = validate_user_create({'username': 'alice', 'email': False})
        assert 'email must be a string' in errors


class TestValidateDeleteReason:
    def test_default_reason_valid(self):
        assert validate_delete_reason({}) == []

    def test_reason_non_string(self):
        errors = validate_delete_reason({'reason': 123})
        assert 'reason must be a string' in errors

    def test_reason_invalid_value(self):
        errors = validate_delete_reason({'reason': 'not_allowed'})
        assert 'reason must be one of policy_cleanup, user_requested, duplicate' in errors


class TestValidateEventType:
    def test_redirected_is_valid(self):
        assert validate_event_type('redirected') == []

    def test_invalid_event_type_rejected(self):
        errors = validate_event_type('invalid')
        assert errors == ['event_type must be one of created, updated, deleted, redirected, click']
