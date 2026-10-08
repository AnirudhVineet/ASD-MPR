def test_index_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Campus Clubs" in resp.data


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_404_page(client):
    resp = client.get("/this-page-does-not-exist")
    assert resp.status_code == 404
    assert b"404" in resp.data
    assert b"Go home" in resp.data


def test_403_page(client, app):
    # /clubs/new requires site_admin; a logged-in regular student is 403, not a redirect
    from tests.helpers import login, make_user

    make_user(app)
    login(client)
    resp = client.get("/clubs/new")
    assert resp.status_code == 403
    assert b"403" in resp.data
    assert b"Go home" in resp.data
