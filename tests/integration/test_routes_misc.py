from app.models.url import Url
import io
from pathlib import Path


def _create_url(client, user_id, url='https://example.com', title='Test'):
    return client.post('/urls', json={'original_url': url, 'title': title, 'user_id': user_id})


def _assert_bulk_users_success_shape(resp, expected_file, expected_row_count):
    body = resp.get_json()
    assert resp.status_code == 201, f'expected 201, got {resp.status_code} with body={body!r}'

    assert isinstance(body, dict), f'expected JSON object body, got {type(body).__name__}: {body!r}'
    assert 'loaded' in body or 'imported' in body, f'missing loaded/imported key in body: {body!r}'
    assert isinstance(body.get('loaded', body.get('imported')), int), (
        f'loaded/imported must be int, got {body.get("loaded", body.get("imported"))!r} in body: {body!r}'
    )
    assert 'row_count' in body, f'missing row_count key in body: {body!r}'
    assert isinstance(body['row_count'], int), f'row_count must be int, got {body["row_count"]!r} in body: {body!r}'
    assert body['row_count'] == expected_row_count, (
        f'expected row_count {expected_row_count}, got {body["row_count"]} in body: {body!r}'
    )
    assert body.get('file') == expected_file, f'expected file {expected_file!r}, got {body.get("file")!r}'

    if resp.status_code == 201:
        assert resp.headers.get('Location') == '/users', (
            f"expected Location '/users', got {resp.headers.get('Location')!r}"
        )


class TestUsersRoutes:
    def test_create_user(self, client):
        payload = {'username': 'testuser_create', 'email': 'testuser_create@example.com'}
        created = client.post('/users', json=payload)

        assert created.status_code == 201
        body = created.get_json()
        assert body['username'] == payload['username']
        assert body['email'] == payload['email']
        assert isinstance(body['id'], int)

    def test_create_user_and_fetch_user_with_urls(self, client):
        create_resp = client.post('/users', json={'username': 'alice', 'email': 'alice@example.com'})
        assert create_resp.status_code == 201
        user_id = create_resp.get_json()['id']

        create_url_resp = _create_url(client, user_id, url='https://example.com/a', title='A')
        assert create_url_resp.status_code == 201

        get_resp = client.get(f'/users/{user_id}')
        assert get_resp.status_code == 200
        data = get_resp.get_json()
        assert data['username'] == 'alice'
        assert len(data['urls']) == 1
        assert data['urls'][0]['short_code'] == create_url_resp.get_json()['short_code']

    def test_create_user_validation_and_not_found(self, client):
        bad_resp = client.post('/users', json={'username': '', 'email': ''})
        assert bad_resp.status_code == 400
        assert set(bad_resp.get_json().keys()) == {'error', 'detail'}

        missing_resp = client.get('/users/99999')
        assert missing_resp.status_code == 404

    def test_create_user_duplicate_username_returns_409_json(self, client):
        first = client.post('/users', json={'username': 'alice', 'email': 'alice@example.com'})
        assert first.status_code == 201

        dup_username = client.post('/users', json={'username': 'alice', 'email': 'alice2@example.com'})
        assert dup_username.status_code == 409
        assert dup_username.get_json() == {
            'error': 'conflict',
            'detail': 'username or email already exists',
        }
        assert set(dup_username.get_json().keys()) == {'error', 'detail'}

    def test_create_user_duplicate_email_returns_409_json(self, client):
        first = client.post('/users', json={'username': 'bob', 'email': 'bob@example.com'})
        assert first.status_code == 201

        dup_email = client.post('/users', json={'username': 'bobby', 'email': 'bob@example.com'})
        assert dup_email.status_code == 409
        assert dup_email.get_json() == {
            'error': 'conflict',
            'detail': 'username or email already exists',
        }
        assert set(dup_email.get_json().keys()) == {'error', 'detail'}

    def test_create_user_exact_duplicate_returns_409_json(self, client):
        first = client.post('/users', json={'username': 'dup', 'email': 'dup@example.com'})
        assert first.status_code == 201

        dup = client.post('/users', json={'username': 'dup', 'email': 'dup@example.com'})
        assert dup.status_code == 409
        assert dup.get_json() == {
            'error': 'conflict',
            'detail': 'username or email already exists',
        }

    def test_bulk_users_rejects_path_escape(self, client):
        resp = client.post('/users/bulk', json={'file': '../users.csv'})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'bad_request'

    def test_list_users_pagination(self, client):
        for i in range(3):
            created = client.post(
                '/users',
                json={'username': f'page_user_{i}', 'email': f'page_user_{i}@example.com'},
            )
            assert created.status_code == 201

        page_1 = client.get('/users?page=1&per_page=2')
        assert page_1.status_code == 200
        assert len(page_1.get_json()) == 2

        page_2 = client.get('/users?page=2&per_page=2')
        assert page_2.status_code == 200
        assert len(page_2.get_json()) == 1

    def test_bulk_load_users_validation(self, client):
        missing_file = client.post('/users/bulk', json={})
        assert missing_file.status_code == 400
        assert missing_file.get_json()['error'] == 'bad_request'

        wrong_ext = client.post('/users/bulk', json={'file': 'users.txt'})
        assert wrong_ext.status_code == 400
        assert wrong_ext.get_json()['error'] == 'bad_request'

    def test_bulk_load_users_with_upload_parses_created_at_resiliently(self, client):
        csv_body = '\n'.join(
            [
                'id,username,email,created_at',
                '1,upload_user_1,upload_user_1@example.com,2026-01-01T00:00:00Z',
                '2,upload_user_2,upload_user_2@example.com,not-a-timestamp',
                '3,,,2026-01-02T00:00:00Z',
            ]
        )
        resp = client.post(
            '/users/bulk',
            data={'file': (io.BytesIO(csv_body.encode('utf-8')), 'users.csv')},
            content_type='multipart/form-data',
        )
        _assert_bulk_users_success_shape(resp, expected_file='users.csv', expected_row_count=2)

        fetched = client.get('/users')
        users = fetched.get_json()
        assert len(users) == 2
        assert users[0]['username'] == 'upload_user_1'
        assert users[1]['username'] == 'upload_user_2'

    def test_bulk_load_users_row_count_fallback_and_missing_file(self, client):
        generated = client.post('/users/bulk', json={'file': 'users.csv', 'row_count': 3})
        _assert_bulk_users_success_shape(generated, expected_file='users.csv', expected_row_count=3)

        listed = client.get('/users')
        assert listed.status_code == 200
        usernames = [u['username'] for u in listed.get_json()]
        assert usernames == ['bulk_user_0001', 'bulk_user_0002', 'bulk_user_0003']

        missing = client.post('/users/bulk', json={'file': 'does-not-exist.csv', 'row_count': 'x'})
        assert missing.status_code == 400
        assert missing.get_json()['error'] == 'bad_request'

    def test_bulk_load_users_seed_file_returns_201_with_location(self, client, monkeypatch, tmp_path):
        seed_dir = Path(tmp_path)
        seed_file = seed_dir / 'users.csv'
        seed_file.write_text(
            '\n'.join(
                [
                    'id,username,email,created_at',
                    '10,seed_user_1,seed_user_1@example.com,2026-01-01T00:00:00Z',
                    '11,seed_user_2,seed_user_2@example.com,',
                ]
            ),
            encoding='utf-8',
        )
        monkeypatch.setattr('app.routes.users.SEED_DIR', str(seed_dir))

        loaded = client.post('/users/bulk', json={'file': 'users.csv'})
        _assert_bulk_users_success_shape(loaded, expected_file='users.csv', expected_row_count=2)

    def test_update_and_delete_user_paths(self, client):
        created = client.post('/users', json={'username': 'upd', 'email': 'upd@example.com'})
        assert created.status_code == 201
        user_id = created.get_json()['id']

        no_fields = client.put(f'/users/{user_id}', json={})
        assert no_fields.status_code == 400

        updated = client.put(f'/users/{user_id}', json={'email': 'upd2@example.com'})
        assert updated.status_code == 200
        assert updated.get_json()['email'] == 'upd2@example.com'

        conflict_base = client.post('/users', json={'username': 'conflict_u', 'email': 'conflict_u@example.com'})
        assert conflict_base.status_code == 201
        conflict = client.put(f'/users/{user_id}', json={'username': 'conflict_u'})
        assert conflict.status_code == 409
        assert conflict.get_json()['error'] == 'conflict'

        deleted = client.delete(f'/users/{user_id}')
        assert deleted.status_code == 200
        assert deleted.get_json()['id'] == user_id

        delete_missing = client.delete('/users/99999')
        assert delete_missing.status_code == 404


class TestEventsRoutes:
    def test_create_event(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/for-event', title='for event')
        assert created.status_code == 201
        url_id = created.get_json()['id']

        resp = client.post(
            '/events',
            json={
                'url_id': url_id,
                'user_id': user.id,
                'event_type': 'click',
                'details': {'referrer': 'https://google.com'},
            },
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body['event_type'] == 'click'
        assert body['url_id'] == url_id
        assert body['user_id'] == user.id
        assert body['details'] == {'referrer': 'https://google.com'}

    def test_list_events_unknown_short_code_returns_empty(self, client):
        resp = client.get('/events?short_code=DOESNTEXIST')
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_list_events_with_filters(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/e1', title='E1')
        short_code = created.get_json()['short_code']

        # Create updated + deleted events
        update_resp = client.put(f'/urls/{short_code}', json={'original_url': 'https://example.com/e1-updated'})
        assert update_resp.status_code == 200
        delete_resp = client.delete(f'/urls/{short_code}', json={'reason': 'duplicate'})
        assert delete_resp.status_code == 200

        url_obj = Url.get(Url.short_code == short_code)

        all_events = client.get('/events')
        assert all_events.status_code == 200
        assert len(all_events.get_json()) >= 3

        by_url_id = client.get(f'/events?url_id={url_obj.id}')
        assert by_url_id.status_code == 200
        assert len(by_url_id.get_json()) == 3

        by_short_code = client.get(f'/events?short_code={short_code}')
        assert by_short_code.status_code == 200
        assert len(by_short_code.get_json()) == 3

        by_event_type = client.get('/events?event_type=deleted')
        assert by_event_type.status_code == 200
        assert any(e['details'].get('reason') == 'duplicate' for e in by_event_type.get_json())

    def test_create_event_rejects_non_object_body(self, client):
        resp = client.post('/events', json='not-an-object')
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'bad_request'

    def test_create_event_rejects_wrong_credential_types(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/typed', title='typed')
        url_id = created.get_json()['id']

        resp = client.post(
            '/events',
            json={
                'url_id': url_id,
                'user_id': '1',
                'event_type': 'click',
                'details': {'referrer': 'https://example.com'},
            },
        )
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'bad_request'

    def test_create_event_unknown_user_rejected(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/unknown-user', title='unknown-user')
        url_id = created.get_json()['id']

        resp = client.post(
            '/events',
            json={
                'url_id': url_id,
                'user_id': 999999,
                'event_type': 'click',
                'details': {'referrer': 'https://example.com'},
            },
        )
        assert resp.status_code == 404
        assert resp.get_json()['error'] == 'not_found'

    def test_create_event_invalid_event_type_rejected(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/invalid-event', title='invalid-event')
        url_id = created.get_json()['id']

        resp = client.post(
            '/events',
            json={
                'url_id': url_id,
                'user_id': user.id,
                'event_type': 'totally-invalid',
                'details': {},
            },
        )
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'bad_request'

    def test_create_event_allows_redirected(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/redirected-event', title='redirected-event')
        url_id = created.get_json()['id']

        resp = client.post(
            '/events',
            json={
                'url_id': url_id,
                'user_id': user.id,
                'event_type': 'redirected',
                'details': {'short_code': created.get_json()['short_code']},
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()['event_type'] == 'redirected'

    def test_list_events_invalid_event_type_rejected(self, client):
        resp = client.get('/events?event_type=totally-invalid')
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'bad_request'

    def test_list_events_can_filter_redirected(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/filter-redirected', title='filter-redirected')
        short_code = created.get_json()['short_code']

        redirect_resp = client.get(f'/r/{short_code}')
        assert redirect_resp.status_code == 302

        filtered = client.get('/events?event_type=redirected')
        assert filtered.status_code == 200
        assert any(event['event_type'] == 'redirected' for event in filtered.get_json())


class TestMetricsAndErrors:
    def test_metrics_endpoint(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200
        data = resp.get_json()
        for key in [
            'cpu_percent',
            'memory_used_mb',
            'memory_total_mb',
            'uptime_seconds',
            'urls_total',
            'urls_active',
            'urls_inactive',
            'events_total',
        ]:
            assert key in data

    def test_500_error_handler_returns_json_and_records_alert(self, app, monkeypatch):
        app.config['PROPAGATE_EXCEPTIONS'] = False
        called = {'count': 0}

        def _fake_record_500_error():
            called['count'] += 1

        monkeypatch.setattr('app.alerting.record_500_error', _fake_record_500_error)

        @app.route('/boom')
        def boom():
            raise RuntimeError('intentional failure for test')

        client = app.test_client()
        resp = client.get('/boom')
        assert resp.status_code == 500
        assert resp.get_json() == {'error': 'internal_error', 'detail': 'an unexpected error occurred'}
        assert called['count'] == 1

    def test_update_url_atomic_when_event_creation_fails(self, app, user, monkeypatch):
        app.config['PROPAGATE_EXCEPTIONS'] = False
        client = app.test_client()

        created = _create_url(client, user.id, url='https://before.example.com', title='Before')
        short_code = created.get_json()['short_code']

        def _fail_event_create(*args, **kwargs):
            raise RuntimeError('forced Event.create failure')

        monkeypatch.setattr('app.routes.urls.Event.create', _fail_event_create)

        update_resp = client.put(
            f'/urls/{short_code}',
            json={'original_url': 'https://after.example.com'},
        )
        assert update_resp.status_code == 500
        assert update_resp.get_json()['error'] == 'internal_error'

        fetched = client.get(f'/urls/{short_code}')
        assert fetched.status_code == 200
        body = fetched.get_json()
        assert body['original_url'] == 'https://before.example.com'
        assert [e['event_type'] for e in body['events']] == ['created']

    def test_health_returns_503_when_database_is_unavailable(self, app, monkeypatch):
        app.config['PROPAGATE_EXCEPTIONS'] = False
        client = app.test_client()

        def _fail_db_check(*args, **kwargs):
            raise RuntimeError('db down')

        monkeypatch.setattr('app.routes.health._check_database', _fail_db_check)

        resp = client.get('/health')
        assert resp.status_code == 503
        body = resp.get_json()
        assert body['status'] == 'degraded'
        assert body['detail'].startswith('database unavailable:')
