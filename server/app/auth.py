"""Emparejamiento y autenticación de dispositivos para la red local.

Modelo:
  * El Mac muestra un código de un solo uso (en un QR). El móvil lo canjea en `POST /api/pair` y recibe una
    cookie de sesión `HttpOnly` (así también funcionan <img>, descargas y fetch sin tocar cabeceras).
  * Los agentes/scripts usan un token `Authorization: Bearer s2p_…` creado con `python -m app.auth token`.
  * En disco solo se guarda el HASH (SHA-256) de tokens y códigos, nunca el valor.
  * Las peticiones desde el propio Mac (loopback) son de confianza, salvo que lleguen por un proxy.

CLI:  python -m app.auth pair | token NOMBRE | list | revoke ID
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

COOKIE = "s2p_session"
TOKEN_PREFIX = "s2p_"
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"   # sin 0/O, 1/I/L, U/V ambiguos
CODE_LEN = 8
CODE_TTL = 600            # s de validez de un código de emparejamiento
MAX_CODES = 5             # códigos activos a la vez
MAX_FAILS, FAIL_WINDOW = 5, 300   # intentos fallidos por IP en 5 minutos
LAST_SEEN_EVERY = 60      # s: cada cuánto se escribe "visto por última vez"
LOOPBACK = {"127.0.0.1", "::1", "localhost"}
PROXY_HEADERS = ("x-forwarded-for", "x-real-ip", "forwarded")

_lock = threading.RLock()
_fails: dict[str, list[float]] = {}


class AuthError(Exception):
    pass


def enabled() -> bool:
    return os.environ.get("SCAN2PRINT_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")


def auth_file() -> Path:
    return Path(os.environ.get("SCAN2PRINT_AUTH_FILE") or Path.home() / "Scan2Print" / "auth.json")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _load() -> dict:
    try:
        data = json.loads(auth_file().read_text())
    except (OSError, ValueError):
        data = {}
    data.setdefault("devices", [])
    data.setdefault("codes", [])
    return data


def _save(data: dict) -> None:
    f = auth_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f"{f.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.chmod(0o600)
    os.replace(tmp, f)


def normalize_code(code: str) -> str:
    return "".join(c for c in str(code).upper() if c.isalnum())


def display_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


# ---------- códigos y dispositivos ----------

def new_code(now: float | None = None) -> tuple[str, int]:
    """Genera un código de un solo uso. Devuelve (código, segundos de validez)."""
    now = time.time() if now is None else now
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))
    with _lock:
        data = _load()
        data["codes"] = [c for c in data["codes"] if c["exp"] > now][-(MAX_CODES - 1):]
        data["codes"].append({"hash": _hash(code), "exp": now + CODE_TTL})
        _save(data)
    return code, CODE_TTL


def _new_device(data: dict, name: str, kind: str, now: float) -> tuple[str, dict]:
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    device = {"id": secrets.token_hex(4), "name": (name or "Dispositivo").strip()[:40], "kind": kind,
              "hash": _hash(token), "created": now, "last_seen": now}
    data["devices"].append(device)
    return token, device


def redeem_code(code: str, name: str, now: float | None = None) -> tuple[str, dict]:
    """Canjea un código (una sola vez) por un token de dispositivo. Lanza AuthError si no vale."""
    now = time.time() if now is None else now
    digest = _hash(normalize_code(code))
    with _lock:
        data = _load()
        data["codes"] = [c for c in data["codes"] if c["exp"] > now]
        hit = next((c for c in data["codes"] if hmac.compare_digest(c["hash"], digest)), None)
        if hit is None:
            _save(data)
            raise AuthError("código no válido o caducado")
        data["codes"].remove(hit)
        token, device = _new_device(data, name, "phone", now)
        _save(data)
    return token, _public(device)


def create_token(name: str, now: float | None = None) -> tuple[str, dict]:
    """Token de larga duración para agentes y scripts (`Authorization: Bearer …`)."""
    now = time.time() if now is None else now
    with _lock:
        data = _load()
        token, device = _new_device(data, name, "api", now)
        _save(data)
    return token, _public(device)


def verify(token: str, now: float | None = None) -> dict | None:
    if not token or not token.startswith(TOKEN_PREFIX):
        return None
    now = time.time() if now is None else now
    digest = _hash(token)
    with _lock:
        data = _load()
        for d in data["devices"]:
            if hmac.compare_digest(d["hash"], digest):
                if now - d.get("last_seen", 0) > LAST_SEEN_EVERY:
                    d["last_seen"] = now
                    _save(data)
                return _public(d)
    return None


def _public(d: dict) -> dict:
    return {k: d[k] for k in ("id", "name", "kind", "created", "last_seen")}


def list_devices() -> list[dict]:
    with _lock:
        return [_public(d) for d in _load()["devices"]]


def has_devices() -> bool:
    return bool(list_devices())


def revoke(device_id: str) -> bool:
    with _lock:
        data = _load()
        keep = [d for d in data["devices"] if d["id"] != device_id]
        if len(keep) == len(data["devices"]):
            return False
        data["devices"] = keep
        _save(data)
        return True


# ---------- límite de intentos ----------

def blocked(ip: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    recent = [t for t in _fails.get(ip, []) if now - t < FAIL_WINDOW]
    _fails[ip] = recent
    return len(recent) >= MAX_FAILS


def register_fail(ip: str, now: float | None = None) -> None:
    _fails.setdefault(ip, []).append(time.time() if now is None else now)


def reset_fails() -> None:
    _fails.clear()


# ---------- identificar una petición ----------

def _local(headers, client_host: str | None) -> bool:
    if os.environ.get("SCAN2PRINT_TRUST_LOCAL", "1") in ("0", "false", "no"):
        return False
    if client_host not in LOOPBACK:
        return False
    return not any(h in headers for h in PROXY_HEADERS)   # detrás de un proxy "loopback" no es el Mac


def identify(headers, cookies, client_host: str | None) -> dict | None:
    """Quién hace la petición: {'via': 'local'|'bearer'|'cookie', ...device} o None si nadie."""
    if _local(headers, client_host):
        return {"id": "local", "name": "Este Mac", "kind": "local", "via": "local"}
    auth = headers.get("authorization", "")
    if auth[:7].lower() == "bearer ":
        dev = verify(auth[7:].strip())
        return {**dev, "via": "bearer"} if dev else None
    dev = verify(cookies.get(COOKIE, ""))
    return {**dev, "via": "cookie"} if dev else None


def same_origin(headers) -> bool:
    """Defensa extra contra CSRF: si el navegador manda Origin, debe ser este mismo servidor."""
    origin = headers.get("origin")
    return origin is None or urlparse(origin).netloc == headers.get("host", "")


# ---------- CLI ----------

def base_url() -> str:
    import socket
    port = os.environ.get("SCAN2PRINT_PORT", "8443")
    return os.environ.get("SCAN2PRINT_URL") or f"https://{socket.gethostname().split('.')[0]}.local:{port}"


def pairing_url(base: str, code: str) -> str:
    return f"{base.rstrip('/')}/#/emparejar/{code}"


def show_pairing(out=None) -> str:
    import segno
    out = out or sys.stdout
    code, ttl = new_code()
    url = pairing_url(base_url(), code)
    print(f"\nEmpareja un móvil: abre esta dirección o escanea el QR (válido {ttl // 60} min, un solo uso)", file=out)
    print(f"  {url}\n  código: {display_code(code)}\n", file=out)
    segno.make(url, error="m").terminal(out=out, compact=True)
    return code


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    cmd = args[0] if args else "help"
    if cmd == "pair":
        show_pairing()
    elif cmd == "token" and len(args) > 1:
        token, dev = create_token(" ".join(args[1:]))
        print(f"Token para «{dev['name']}» (id {dev['id']}). Guárdalo: no se vuelve a mostrar.\n  {token}\n"
              "Úsalo así: curl -H 'Authorization: Bearer <token>' https://…/api/jobs")
    elif cmd == "list":
        for d in list_devices():
            day = time.strftime("%Y-%m-%d", time.localtime(d["created"]))
            print(f"{d['id']}  {d['kind']:5}  {d['name']}  (creado {day})")
    elif cmd == "revoke" and len(args) > 1:
        print("revocado" if revoke(args[1]) else "no existe ese id")
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
