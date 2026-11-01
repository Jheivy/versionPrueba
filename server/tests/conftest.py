import pytest


@pytest.fixture(autouse=True)
def _auth_off_by_default(monkeypatch, tmp_path):
    """Las pruebas de la API no se emparejan: la autenticación va desactivada salvo en test_auth.py
    (que la activa). El almacén de dispositivos va a un directorio temporal, nunca a ~/Scan2Print."""
    monkeypatch.setenv("SCAN2PRINT_AUTH", "off")
    monkeypatch.setenv("SCAN2PRINT_AUTH_FILE", str(tmp_path / "auth.json"))
    from app import auth
    auth.reset_fails()
