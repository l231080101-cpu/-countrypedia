def test_health(client):
    resp = client.get('/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'CountryPedia API' in data['message']


def test_register(client):
    resp = client.post('/api/register', json={
        'username': 'newuser',
        'email': 'new@test.com',
        'password': 'TestPass123'
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['user']['username'] == 'newuser'


def test_register_duplicate(client):
    client.post('/api/register', json={
        'username': 'dupuser',
        'email': 'dup_1@test.com',
        'password': 'TestPass123'
    })
    resp = client.post('/api/register', json={
        'username': 'dupuser',
        'email': 'dup_2@test.com',
        'password': 'TestPass123'
    })
    assert resp.status_code == 400
    assert 'ya existe' in resp.get_json()['error']


def test_register_duplicate_email(client):
    client.post('/api/register', json={
        'username': 'email1',
        'email': 'dupe@test.com',
        'password': 'TestPass123'
    })
    resp = client.post('/api/register', json={
        'username': 'email2',
        'email': 'dupe@test.com',
        'password': 'TestPass123'
    })
    assert resp.status_code == 400


def test_register_short_password(client):
    resp = client.post('/api/register', json={
        'username': 'shortpwd',
        'email': 'short@test.com',
        'password': '12345'
    })
    assert resp.status_code == 400


def test_register_weak_password(client):
    resp = client.post('/api/register', json={
        'username': 'weakpwd',
        'email': 'weak@test.com',
        'password': 'onlylower'
    })
    assert resp.status_code == 400
    err = resp.get_json()['error']
    assert 'mayúscula' in err


def test_register_no_digit_password(client):
    resp = client.post('/api/register', json={
        'username': 'nodigit',
        'email': 'nodigit@test.com',
        'password': 'NoDigitsHere'
    })
    assert resp.status_code == 400
    err = resp.get_json()['error']
    assert 'número' in err


def test_register_invalid_email(client):
    resp = client.post('/api/register', json={
        'username': 'bademail',
        'email': 'not-an-email',
        'password': 'TestPass123'
    })
    assert resp.status_code == 400
    assert 'email' in resp.get_json()['error'].lower()


def test_register_short_username(client):
    resp = client.post('/api/register', json={
        'username': 'ab',
        'email': 'ab@test.com',
        'password': 'TestPass123'
    })
    assert resp.status_code == 400


def test_register_invalid_username(client):
    resp = client.post('/api/register', json={
        'username': 'user name!',
        'email': 'valid@test.com',
        'password': 'TestPass123'
    })
    assert resp.status_code == 400


def test_login(client):
    reg = client.post('/api/register', json={
        'username': 'loginuser',
        'email': 'login@test.com',
        'password': 'TestPass123'
    })
    assert reg.status_code == 201, f"Register failed: {reg.get_json()}"
    resp = client.post('/api/login', json={
        'username': 'loginuser',
        'password': 'TestPass123'
    })
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    data = resp.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data


def test_login_wrong_password(client):
    client.post('/api/register', json={
        'username': 'wrongpass',
        'email': 'wrong@test.com',
        'password': 'TestPass123'
    })
    resp = client.post('/api/login', json={
        'username': 'wrongpass',
        'password': 'WrongPass123'
    })
    assert resp.status_code == 401


def test_login_nonexistent(client):
    resp = client.post('/api/login', json={
        'username': 'nobody',
        'password': 'TestPass123'
    })
    assert resp.status_code == 401


def test_refresh(client):
    reg_resp = client.post('/api/register', json={
        'username': 'refreshuser',
        'email': 'refresh@test.com',
        'password': 'TestPass123'
    })
    assert reg_resp.status_code == 201, f"Register failed: {reg_resp.get_json()}"
    refresh_token = reg_resp.get_json()['refresh_token']
    resp = client.post('/api/refresh', json={
        'refresh_token': refresh_token
    })
    assert resp.status_code == 200
    assert 'access_token' in resp.get_json()


def test_refresh_invalid(client):
    resp = client.post('/api/refresh', json={
        'refresh_token': 'not-a-real-token'
    })
    assert resp.status_code == 400


def test_me(client, auth_data):
    resp = client.get('/api/me', headers={
        'Authorization': f"Bearer {auth_data['access_token']}"
    })
    assert resp.status_code == 200
    assert resp.get_json()['username'] == auth_data['user']['username']


def test_me_no_token(client):
    resp = client.get('/api/me')
    assert resp.status_code == 401


def test_me_expired_token(client):
    resp = client.get('/api/me', headers={
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE1MDAwMDAwMDB9.fake'
    })
    assert resp.status_code == 401


def test_logout(client, auth_data):
    resp = client.post('/api/logout', json={
        'refresh_token': auth_data['refresh_token'],
        'access_token': auth_data['access_token']
    }, headers={
        'Authorization': f"Bearer {auth_data['access_token']}"
    })
    assert resp.status_code == 200


def test_logout_revokes_access_token(client, auth_data):
    client.post('/api/logout', json={
        'refresh_token': auth_data['refresh_token'],
        'access_token': auth_data['access_token']
    }, headers={
        'Authorization': f"Bearer {auth_data['access_token']}"
    })
    resp = client.get('/api/me', headers={
        'Authorization': f"Bearer {auth_data['access_token']}"
    })
    assert resp.status_code == 401


def test_search_pais(client):
    resp = client.get('/api/buscar/France')
    assert resp.status_code == 200, f"Search failed: {resp.get_json()}"
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_search_pais_not_found(client):
    resp = client.get('/api/buscar/zzzzzzznonexistent')
    assert resp.status_code == 404


def test_region(client):
    resp = client.get('/api/region/Europe')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_populares(client):
    resp = client.get('/api/populares')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert 'pais' in data[0]
        assert 'conteo' in data[0]


def test_favorites_crud(client, auth_headers):
    headers = auth_headers
    resp = client.post('/api/favoritos', json={'cca3': 'FRA'}, headers=headers)
    assert resp.status_code == 201

    resp = client.get('/api/favoritos', headers=headers)
    assert resp.status_code == 200
    favs = resp.get_json()
    assert isinstance(favs, list)
    assert any(f['cca3'] == 'FRA' for f in favs)

    resp = client.delete('/api/favoritos/FRA', headers=headers)
    assert resp.status_code == 200

    resp = client.get('/api/favoritos', headers=headers)
    assert resp.status_code == 200
    favs = resp.get_json()
    assert not any(f['cca3'] == 'FRA' for f in favs)


def test_favorites_requires_token(client, api_key):
    resp = client.post('/api/favoritos', json={'cca3': 'FRA'})
    assert resp.status_code == 401
    assert resp.status_code == 401


def test_cambio(client):
    resp = client.get('/api/cambio/EUR')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'tasa' in data


def test_cambio_unsupported(client):
    resp = client.get('/api/cambio/ZZZ')
    assert resp.status_code in (404, 500)


def test_costos(client):
    resp = client.get('/api/costo-vida/France')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'factor' in data
    assert 'costs_usd' in data
    for key in ('comida', 'transporte', 'alojamiento', 'entretenimiento', 'servicios'):
        assert key in data['costs_usd']


def test_travel_advisory(client):
    resp = client.get('/api/travel-advisory/France')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'visa_required' in data or 'safety_level' in data


def test_travel_advisory_unknown(client):
    resp = client.get('/api/travel-advisory/Atlantis')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'visa_required' in data


def test_weather_no_key(client):
    resp = client.get('/api/weather/France')
    assert resp.status_code == 503


def test_news_no_key(client):
    resp = client.get('/api/noticias/France')
    assert resp.status_code == 503


def test_404(client):
    resp = client.get('/api/nonexistent')
    assert resp.status_code == 404
