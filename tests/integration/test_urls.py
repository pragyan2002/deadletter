import json


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


class TestRedirect:
    def test_active_url_redirects(self, client, user):
        r = _create_url(client, user.id, url='https://target.example.com')
        code = r.get_json()['short_code']

        r2 = client.get(f'/r/{code}')
        assert r2.status_code == 302
        assert r2.headers['Location'] == 'https://target.example.com'

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
