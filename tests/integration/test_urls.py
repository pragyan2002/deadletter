import json
from datetime import datetime, timedelta, timezone
from time import perf_counter, sleep


def _create_url(client, user_id, url='https://example.com', title='Test'):
    return client.post('/urls', json={'original_url': url, 'title': title, 'user_id': user_id})


class TestHealth:
    def test_health(self, client):
        r = client.get('/health')
        assert r.status_code == 200
        assert r.get_json()['status'] == 'ok'


class TestCreateUrl:
    def test_creates_url_and_event(self, client, user):
        r = _create_url(client, user.id)
        assert r.status_code == 201
        data = r.get_json()
        assert len(data['short_code']) == 6
        assert data['is_active'] is True

        # event was created
        r2 = client.get(f"/urls/{data['short_code']}")
        assert r2.status_code == 200
        events = r2.get_json()['events']
        assert len(events) == 1
        assert events[0]['event_type'] == 'created'

    def test_bad_scheme_rejected(self, client, user):
        r = _create_url(client, user.id, url='ftp://bad.com')
        assert r.status_code == 400
        body = r.get_json()
        assert 'error' in body and 'detail' in body

    def test_unknown_user_404(self, client):
        r = _create_url(client, user_id=99999)
        assert r.status_code == 404

    def test_missing_fields_400(self, client, user):
        r = client.post('/urls', json={'user_id': user.id})
        assert r.status_code == 400

    def test_non_string_original_url_rejected(self, client, user):
        r = client.post('/urls', json={'original_url': 123, 'title': 'ok', 'user_id': user.id})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'bad_request'

    def test_non_string_title_rejected(self, client, user):
        r = client.post('/urls', json={'original_url': 'https://example.com', 'title': 123, 'user_id': user.id})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'bad_request'

    def test_repeated_creates_generate_distinct_short_codes(self, client, user):
        r1 = _create_url(client, user.id, url='https://example.com/one', title='One')
        r2 = _create_url(client, user.id, url='https://example.com/two', title='Two')
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.get_json()['short_code'] != r2.get_json()['short_code']

    def test_retries_short_code_collision_and_succeeds(self, client, user, monkeypatch):
        from app.routes import urls as urls_routes
        code_iter = iter(['AAAAAA', 'AAAAAA', 'BBBBBB'])
        monkeypatch.setattr(urls_routes, '_generate_short_code', lambda: next(code_iter))

        first = _create_url(client, user.id, url='https://example.com/first', title='First')
        second = _create_url(client, user.id, url='https://example.com/second', title='Second')

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.get_json()['short_code'] == 'AAAAAA'
        assert second.get_json()['short_code'] == 'BBBBBB'

    def test_create_url_rejects_non_json_content_type(self, client, user):
        resp = client.post(
            '/urls',
            data=json.dumps({'original_url': 'https://example.com', 'title': 'ok', 'user_id': user.id}),
            content_type='text/plain',
        )
        assert resp.status_code == 415
        assert resp.get_json()['error'] == 'unsupported_media_type'

    def test_create_url_supports_expires_at(self, client, user):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        resp = client.post(
            '/urls',
            json={'original_url': 'https://example.com/exp', 'title': 'exp', 'user_id': user.id, 'expires_at': future},
        )
        assert resp.status_code == 201
        assert resp.get_json()['expires_at'] is not None


class TestRedirect:
    def test_active_url_redirects(self, client, user):
        r = _create_url(client, user.id, url='https://target.example.com')
        code = r.get_json()['short_code']

        r2 = client.get(f'/r/{code}')
        assert r2.status_code == 302
        assert r2.headers['Location'] == 'https://target.example.com'

        for _ in range(20):
            details = client.get(f'/urls/{code}')
            events = details.get_json()['events']
            if events and events[-1]['event_type'] == 'redirected':
                break
            sleep(0.02)
        assert events[-1]['event_type'] == 'redirected'

    def test_missing_short_code_404_json(self, client):
        r = client.get('/r/XXXXXX')
        assert r.status_code == 404
        body = r.get_json()
        assert body['error'] == 'not_found'

    def test_inactive_url_404_not_redirect(self, client, user):
        r = _create_url(client, user.id, url='https://example.com')
        code = r.get_json()['short_code']

        client.delete(f'/urls/{code}', json={'reason': 'user_requested'})

        r2 = client.get(f'/r/{code}')
        assert r2.status_code == 404
        body = r2.get_json()
        assert body['error'] == 'not_found'

        details = client.get(f'/urls/{code}')
        event_types = [event['event_type'] for event in details.get_json()['events']]
        assert 'redirected' not in event_types

    def test_active_url_redirects_from_details_endpoint(self, client, user):
        r = _create_url(client, user.id, url='https://example.com/redirect-target')
        data = r.get_json()

        by_code = client.get(f"/urls/{data['short_code']}/redirect")
        assert by_code.status_code == 302
        assert by_code.headers['Location'] == 'https://example.com/redirect-target'

        by_id = client.get(f"/urls/{data['id']}/redirect")
        assert by_id.status_code == 302
        assert by_id.headers['Location'] == 'https://example.com/redirect-target'

    def test_expired_url_404_and_no_redirect_event(self, client, user):
        expired = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        created = client.post(
            '/urls',
            json={
                'original_url': 'https://example.com/expired',
                'title': 'Expired',
                'user_id': user.id,
                'expires_at': expired,
            },
        )
        assert created.status_code == 201
        code = created.get_json()['short_code']

        redirect_resp = client.get(f'/r/{code}')
        assert redirect_resp.status_code == 404
        assert redirect_resp.get_json()['error'] == 'not_found'

        details = client.get(f'/urls/{code}')
        event_types = [event['event_type'] for event in details.get_json()['events']]
        assert 'redirected' not in event_types

    def test_redirect_is_non_blocking_when_event_write_is_slow(self, client, user, monkeypatch):
        from app.models.event import Event

        created = _create_url(client, user.id, url='https://example.com/slow', title='Slow')
        code = created.get_json()['short_code']

        original_create = Event.create

        def slow_create(*args, **kwargs):
            sleep(0.2)
            return original_create(*args, **kwargs)

        monkeypatch.setattr(Event, 'create', slow_create)

        started = perf_counter()
        resp = client.get(f'/r/{code}')
        elapsed = perf_counter() - started

        assert resp.status_code == 302
        assert elapsed < 0.15


class TestUpdateUrl:
    def test_update_original_url(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.put(f'/urls/{code}', json={'original_url': 'https://new.example.com'})
        assert r.status_code == 200
        assert r.get_json()['original_url'] == 'https://new.example.com'

        # updated event logged
        events = client.get(f'/urls/{code}').get_json()['events']
        types = [e['event_type'] for e in events]
        assert 'updated' in types

    def test_update_inactive_url_404(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        client.delete(f'/urls/{code}', json={'reason': 'user_requested'})
        r = client.put(f'/urls/{code}', json={'title': 'New title'})
        assert r.status_code == 404

    def test_empty_body_400(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.put(f'/urls/{code}', json={})
        assert r.status_code == 400

    def test_update_non_string_fields_rejected(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.put(f'/urls/{code}', json={'original_url': 123})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'bad_request'

        r2 = client.put(f'/urls/{code}', json={'title': 456})
        assert r2.status_code == 400
        assert r2.get_json()['error'] == 'bad_request'


class TestDeleteUrl:
    def test_soft_delete(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.delete(f'/urls/{code}', json={'reason': 'user_requested'})
        assert r.status_code == 200
        assert r.get_json()['is_active'] is False

    def test_double_delete_409(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        client.delete(f'/urls/{code}', json={'reason': 'user_requested'})
        r = client.delete(f'/urls/{code}', json={'reason': 'user_requested'})
        assert r.status_code == 409

    def test_deleted_event_logged(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        client.delete(f'/urls/{code}', json={'reason': 'duplicate'})
        events = client.get(f'/urls/{code}').get_json()['events']
        deleted = [e for e in events if e['event_type'] == 'deleted']
        assert len(deleted) == 1
        assert deleted[0]['details']['reason'] == 'duplicate'

    def test_invalid_delete_reason_rejected(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.delete(f'/urls/{code}', json={'reason': 'invalid'})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'bad_request'

    def test_non_string_delete_reason_rejected(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.delete(f'/urls/{code}', json={'reason': 42})
        assert r.status_code == 400
        assert r.get_json()['error'] == 'bad_request'

    def test_delete_accepts_empty_body(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.delete(f'/urls/{code}')
        assert r.status_code == 200
        assert r.get_json()['is_active'] is False

    def test_delete_accepts_json_null_body(self, client, user):
        code = _create_url(client, user.id).get_json()['short_code']
        r = client.delete(f'/urls/{code}', data='null', content_type='application/json')
        assert r.status_code == 200
        assert r.get_json()['is_active'] is False


class TestErrorShape:
    def test_404_is_json(self, client):
        r = client.get('/urls/NOTEXIST')
        assert r.status_code == 404
        body = r.get_json()
        assert set(body.keys()) == {'error', 'detail'}

    def test_400_is_json(self, client, user):
        r = client.post('/urls', json={'user_id': user.id})
        assert r.status_code == 400
        body = r.get_json()
        assert set(body.keys()) == {'error', 'detail'}

    def test_unknown_short_code_endpoints_return_json_not_html(self, client):
        for method, path in [
            ('GET', '/urls/NOTEXIST'),
            ('GET', '/r/NOTEXIST'),
            ('PUT', '/urls/NOTEXIST'),
            ('DELETE', '/urls/NOTEXIST'),
        ]:
            if method == 'GET':
                r = client.get(path)
            elif method == 'PUT':
                r = client.put(path, json={'title': 'ignored'})
            else:
                r = client.delete(path, json={'reason': 'user_requested'})

            assert r.status_code == 404
            assert r.is_json
            assert r.content_type.startswith('application/json')
            assert r.get_json()['error'] == 'not_found'


class TestUrlIdRoutesAndList:
    def test_get_put_delete_by_id(self, client, user):
        created = _create_url(client, user.id, url='https://example.com/by-id', title='By ID')
        body = created.get_json()
        url_id = body['id']

        by_id = client.get(f'/urls/{url_id}')
        assert by_id.status_code == 200
        assert by_id.get_json()['short_code'] == body['short_code']

        updated = client.put(f'/urls/{url_id}', json={'title': 'Updated via ID'})
        assert updated.status_code == 200
        assert updated.get_json()['title'] == 'Updated via ID'

        deleted = client.delete(f'/urls/{url_id}', json={'reason': 'user_requested'})
        assert deleted.status_code == 200
        assert deleted.get_json()['is_active'] is False

    def test_list_urls_filters_and_pagination(self, client, user):
        _create_url(client, user.id, url='https://example.com/a', title='A')
        _create_url(client, user.id, url='https://example.com/b', title='B')

        all_urls = client.get('/urls')
        assert all_urls.status_code == 200
        assert isinstance(all_urls.get_json(), list)
        assert len(all_urls.get_json()) == 2

        by_user = client.get(f'/urls?user_id={user.id}')
        assert by_user.status_code == 200
        assert len(by_user.get_json()) == 2

        first_id = all_urls.get_json()[0]['id']
        deactivated = client.put(f'/urls/{first_id}', json={'is_active': False})
        assert deactivated.status_code == 200
        assert deactivated.get_json()['is_active'] is False

        active_only = client.get('/urls?is_active=true')
        assert active_only.status_code == 200
        assert all(u['is_active'] is True for u in active_only.get_json())

        paged = client.get('/urls?page=1&per_page=1')
        assert paged.status_code == 200
        assert len(paged.get_json()) == 1

    def test_bulk_load_urls_validation_errors(self, client):
        missing_file = client.post('/urls/bulk', json={})
        assert missing_file.status_code == 400
        assert missing_file.get_json()['error'] == 'bad_request'

        wrong_extension = client.post('/urls/bulk', json={'file': 'users.txt'})
        assert wrong_extension.status_code == 400
        assert wrong_extension.get_json()['error'] == 'bad_request'
