def test_upload_and_list_sessions(client):
    # create user
    r = client.post('/v1/auth/login', json={'email':'user2@example.com','password':'p'})
    assert r.status_code == 200
    token = r.json()['access_token']

    payload = {
        'sessions':[{
            'client_session_id':'1_20250101',
            'started_at_utc':'2025-01-01T10:00:00Z',
            'ended_at_utc':'2025-01-01T10:10:00Z',
            'total_blinks':42,
            'device_id':'dev1',
            'app_version':'1.0.0',
            'avg_cpu_percent': 12.5,
            'avg_memory_mb': 300.2,
            'energy_impact':'Low'
        }]
    }
    r2 = client.post('/v1/sessions', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert r2.status_code == 200
    r3 = client.get('/v1/sessions', headers={'Authorization': f'Bearer {token}'})
    assert r3.status_code == 200
    sessions = r3.json()
    assert len(sessions) == 1
    assert sessions[0]['total_blinks'] == 42


def test_blink_summary_fallback_sessions(client):
    # create user
    r = client.post('/v1/auth/login', json={'email':'user3@example.com','password':'p'})
    token = r.json()['access_token']
    # upload session only
    payload = {
        'sessions':[{
            'client_session_id':'2_20250101',
            'started_at_utc':'2025-01-01T11:00:00Z',
            'ended_at_utc':'2025-01-01T11:05:00Z',
            'total_blinks':10,
            'device_id':'devA',
            'app_version':'1.0.0'
        }]
    }
    client.post('/v1/sessions', json=payload, headers={'Authorization': f'Bearer {token}'})
    # summary should use tracking_sessions source
    rsum = client.get('/v1/blinks/summary', headers={'Authorization': f'Bearer {token}'})
    assert rsum.status_code == 200
    data = rsum.json()
    assert data['total_blinks'] == 10
    assert data['source'] == 'tracking_sessions'
