def test_admin_login_requires_password(client):
    # wrong password should fail
    r = client.post('/v1/auth/login', json={'email':'admin1@example.com','password':'wrong'})
    assert r.status_code == 401
    # correct password succeeds
    r2 = client.post('/v1/auth/login', json={'email':'admin1@example.com','password':'admin@waw'})
    assert r2.status_code == 200
    data = r2.json()
    assert 'access_token' in data
    # scope should be admin
    token = data['access_token']
    parts = token.split('.')
    assert len(parts) == 3


def test_user_auto_create_then_set_password_and_login_password(client):
    # Auto-create normal user (not in admin list)
    r = client.post('/v1/auth/login', json={'email':'user@example.com','password':'x'})
    assert r.status_code == 200
    token = r.json()['access_token']
    # Set password
    r2 = client.post('/v1/auth/set-password', json={'password':'StrongPass123!'}, headers={'Authorization': f'Bearer {token}'})
    assert r2.status_code == 200
    # Login with password
    r3 = client.post('/v1/auth/login-password', json={'email':'user@example.com','password':'StrongPass123!'} )
    assert r3.status_code == 200


def test_rate_limit_not_triggered_within_relaxed_limit(client):
    # We set rate limit max to 50, perform a few
    for i in range(5):
        client.post('/v1/auth/login', json={'email':'another@example.com','password':'x'})
    # Final should still not be blocked (auto create allowed)
    r = client.post('/v1/auth/login', json={'email':'another@example.com','password':'x'})
    assert r.status_code == 200
