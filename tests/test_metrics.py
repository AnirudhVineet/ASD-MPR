from .helpers import login, make_user


def test_metrics_exposes_http_and_business_metrics(client, app):
    make_user(app)
    login(client)
    client.get("/clubs/")
    client.get("/clubs/12345")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'http_requests_total{endpoint="/clubs/",method="GET",status="200"}' in body
    # Raw IDs must not leak into labels; the URL rule is used instead
    assert 'endpoint="/clubs/<int:club_id>",method="GET",status="404"' in body
    assert "http_request_duration_seconds_bucket" in body
    assert "clubapp_users 1.0" in body
    assert "clubapp_clubs 0.0" in body
    assert 'clubapp_logins_total{result="success"}' in body
