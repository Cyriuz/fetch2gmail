"""
UI auth: OAuth only (no username/password). When credentials.json exists, require Google sign-in.
Session cookie signed with .cookie_secret (one file next to config). No database.
"""

import base64
import hmac
import secrets
import time
from pathlib import Path

from fastapi import Request, Response
from fastapi.responses import RedirectResponse

COOKIE_NAME = "fetch2gmail_session"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days
SESSION_VALIDITY = 7 * 24 * 3600  # 7 days

COOKIE_SECRET_FILE = ".cookie_secret"


def _credentials_exist(config_dir: Path | None) -> bool:
    if not config_dir:
        return False
    return (config_dir / "credentials.json").exists()


def get_or_create_cookie_secret(config_dir: Path) -> bytes:
    """Persisted secret for signing OAuth session cookies. One file, no DB."""
    path = config_dir / COOKIE_SECRET_FILE
    if path.exists():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.write_bytes(secret)
    return secret


def auth_required(config_dir: Path | None = None, config_exists: bool = True) -> bool:
    """True if we require login: credentials.json present → OAuth only."""
    return _credentials_exist(config_dir)


def _get_secret_for_cookie(config_dir: Path | None) -> bytes:
    """Secret used to sign session cookie (file-based)."""
    if config_dir:
        return get_or_create_cookie_secret(config_dir)
    return b""


def _sign(value: str, secret: bytes) -> str:
    if not secret:
        return ""
    sig = hmac.new(secret, value.encode("utf-8"), "sha256").digest()
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def _verify_cookie(cookie_value: str | None, secret: bytes) -> bool:
    if not cookie_value or not secret:
        return False
    try:
        parts = cookie_value.split(".")
        if len(parts) != 2:
            return False
        sig, expiry_str = parts[0], parts[1]
        expiry = int(expiry_str)
        if time.time() > expiry:
            return False
        expected = _sign(expiry_str, secret)
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def create_session_cookie_value(secret: bytes) -> str:
    expiry = int(time.time()) + SESSION_VALIDITY
    sig = _sign(str(expiry), secret)
    return f"{sig}.{expiry}"


def verify_request(request: Request, config_dir: Path | None = None, config_exists: bool = True) -> bool:
    """Return True if request has a valid session (or auth not required)."""
    if not auth_required(config_dir, config_exists):
        return True
    secret = _get_secret_for_cookie(config_dir)
    if not secret:
        return False
    cookie = request.cookies.get(COOKIE_NAME)
    return _verify_cookie(cookie, secret)


def set_session_cookie(response: Response, config_dir: Path | None = None) -> None:
    """Set the session cookie on response (uses password or file-based secret)."""
    secret = _get_secret_for_cookie(config_dir)
    if not secret:
        return
    value = create_session_cookie_value(secret)
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
