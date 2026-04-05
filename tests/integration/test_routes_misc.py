from app.models.url import Url


def _create_url(client, user_id, url='https://example.com', title='Test'):
    return client.post('/urls', json={'original_url': url, 'title': title, 'user_id': user_id})


class TestUsersRoutes:
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


class TestEventsRoutes:
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
