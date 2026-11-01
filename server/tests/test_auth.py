import json

import pytest
from fastapi.testclient import TestClient

from app import auth, main

LAN = ("192.168.1.50", 50000)          # un móvil de la Wi-Fi
HOST = "https://scan2print.local:8443"


@pytest.fixture(autouse=True)
def auth_on(monkeypatch, tmp_path):
    monkeypatch.setenv("SCAN2PRINT_AUTH", "on")
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")


def phone():
    return TestClient(main.app, base_url=HOST, client=LAN)


def mac():
    return TestClient(main.app, base_url=HOST, client=("127.0.0.1", 50000))


def pair(client, name="Mi móvil"):
    code = mac().post("/api/pairing-code").json()["code"]
    r = client.post("/api/pair", json={"code": code, "name": name})
    assert r.status_code == 200, r.text
    return r


def test_api_needs_pairing_but_the_app_shell_does_not():
    c = phone()
    for path in ("/api/jobs", "/api/health", "/api/devices", "/api/marker-sheet.pdf"):
        r = c.get(path)
        assert r.status_code == 401 and r.json() == {"detail": "no autorizado"}, path
    assert c.get("/").status_code == 200 and c.get("/sw.js").status_code == 200  # se puede cargar la app para emparejar
    st = c.get("/api/auth/status").json()
    assert st == {"required": True, "authenticated": False, "device": None, "local": False}


def test_the_mac_itself_is_trusted_unless_behind_a_proxy(monkeypatch):
    assert mac().get("/api/jobs").status_code == 200
    assert mac().get("/api/jobs", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 401
    monkeypatch.setenv("SCAN2PRINT_TRUST_LOCAL", "0")
    assert mac().get("/api/jobs").status_code == 401


def test_pairing_flow_sets_a_hardened_cookie_and_stores_only_hashes(tmp_path):
    c = phone()
    r = pair(c)
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "secure" in cookie and "max-age=31536000" in cookie
    assert c.get("/api/jobs").status_code == 200
    assert c.get("/api/auth/status").json()["device"] == "Mi móvil"
    raw = phone().cookies  # un móvil sin emparejar sigue fuera
    assert not raw and phone().get("/api/jobs").status_code == 401
    stored = (tmp_path / "auth.json").read_text()
    token = c.cookies.get(auth.COOKIE)
    assert token.startswith("s2p_") and token not in stored        # el token en claro nunca toca el disco
    assert json.loads(stored)["devices"][0]["hash"] == auth._hash(token)
    assert oct((tmp_path / "auth.json").stat().st_mode & 0o777) == "0o600"


def test_code_is_single_use_and_forgiving_about_format():
    code = mac().post("/api/pairing-code").json()["code"]
    typed = f" {code[:4].lower()}-{code[4:].lower()} "              # minúsculas, guion y espacios
    assert phone().post("/api/pair", json={"code": typed, "name": "A"}).status_code == 200
    assert phone().post("/api/pair", json={"code": code, "name": "B"}).status_code == 401  # ya canjeado


def test_expired_code_is_rejected():
    code, _ = auth.new_code(now=1000.0)                              # caducó hace décadas
    r = phone().post("/api/pair", json={"code": code, "name": "tarde"})
    assert r.status_code == 401 and "caducado" in r.json()["detail"]


def test_brute_force_is_throttled_even_with_a_valid_code_afterwards():
    c = phone()
    for _ in range(auth.MAX_FAILS):
        assert c.post("/api/pair", json={"code": "AAAAAAAA", "name": "x"}).status_code == 401
    good = mac().post("/api/pairing-code").json()["code"]
    assert c.post("/api/pair", json={"code": good, "name": "x"}).status_code == 429  # bloqueada la IP
    assert TestClient(main.app, base_url=HOST, client=("192.168.1.77", 1)).post(      # otra IP no se ve afectada
        "/api/pair", json={"code": good, "name": "y"}).status_code == 200


def test_agents_use_bearer_tokens_and_can_be_revoked():
    token, dev = auth.create_token("agente de impresión")
    c = phone()
    assert c.get("/api/jobs", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert c.get("/api/jobs", headers={"Authorization": "Bearer s2p_inventado"}).status_code == 401
    assert c.get("/api/jobs", headers={"Authorization": "Bearer algo-raro"}).status_code == 401
    assert auth.revoke(dev["id"])
    assert c.get("/api/jobs", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_cookie_sessions_reject_cross_site_writes_but_bearer_does_not_need_to():
    c = phone()
    pair(c)
    evil = {"Origin": "https://evil.example"}
    assert c.post("/api/pairing-code", headers=evil).status_code == 403                # CSRF con cookie
    assert c.post("/api/pairing-code", headers={"Origin": HOST}).status_code == 200    # la propia app
    assert c.get("/api/jobs", headers=evil).status_code == 200                          # lecturas: SameSite ya protege
    token, _ = auth.create_token("script")
    bearer = {"Authorization": f"Bearer {token}", **evil}
    assert phone().post("/api/pairing-code", headers=bearer).status_code == 200        # no usa cookie: no hay CSRF


def test_devices_list_revoke_and_logout():
    a, b = phone(), phone()
    pair(a, "Móvil A")
    pair(b, "Móvil B")
    devs = a.get("/api/devices").json()
    assert {d["name"] for d in devs} == {"Móvil A", "Móvil B"}
    assert [d["name"] for d in devs if d["current"]] == ["Móvil A"]
    assert all("hash" not in d for d in devs)                                           # nunca se exponen hashes
    other = next(d["id"] for d in devs if d["name"] == "Móvil B")
    assert a.delete(f"/api/devices/{other}").status_code == 204
    assert b.get("/api/jobs").status_code == 401                                        # B quedó fuera
    assert a.delete("/api/devices/noexiste").status_code == 404
    assert a.post("/api/auth/logout").status_code == 200
    assert a.get("/api/jobs").status_code == 401                                        # A cerró sesión


def test_qr_is_an_svg_and_private():
    code = mac().post("/api/pairing-code").json()["code"]
    r = mac().get("/api/pairing/qr.svg", params={"code": code})
    assert r.status_code == 200 and r.headers["content-type"] == "image/svg+xml" and "<svg" in r.text
    assert phone().get("/api/pairing/qr.svg", params={"code": code}).status_code == 401
    assert mac().post("/api/pairing-code").json()["url"].startswith(f"{HOST}/#/emparejar/")


def test_auth_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_AUTH", "off")
    c = phone()
    assert c.get("/api/jobs").status_code == 200
    assert c.get("/api/auth/status").json()["required"] is False


def test_cli_creates_lists_and_revokes(capsys):
    assert auth.main(["token", "agente de pruebas"]) == 0
    out = capsys.readouterr().out
    token = next(w for w in out.split() if w.startswith("s2p_"))
    assert auth.verify(token)["name"] == "agente de pruebas"
    auth.main(["list"])
    listing = capsys.readouterr().out
    assert "agente de pruebas" in listing
    dev_id = listing.split()[0]
    auth.main(["revoke", dev_id])
    assert auth.verify(token) is None


def test_first_start_prints_a_pairing_qr_only_while_unpaired(capsys):
    with TestClient(main.app):
        out = capsys.readouterr().out
    assert "Empareja un móvil" in out and "#/emparejar/" in out
    assert any(ch in out for ch in "█▀▄")                  # y el QR en la terminal
    auth.create_token("ya emparejado")
    with TestClient(main.app):
        assert "Empareja un móvil" not in capsys.readouterr().out


def test_no_public_api_docs():
    c = phone()
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert c.get(path).status_code == 404, path
