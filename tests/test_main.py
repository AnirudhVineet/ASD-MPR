def test_index_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Campus Clubs" in resp.data


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
