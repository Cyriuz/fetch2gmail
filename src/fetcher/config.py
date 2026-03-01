"""Configuration loading from JSON and environment variables."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from current dir and common locations
load_dotenv()
for p in (Path.cwd(), Path.home(), Path(__file__).resolve().parents[2]):
    load_dotenv(p / ".env")


def load_config(path: str | Path, resolve_password: bool = True) -> dict[str, Any]:
    """Load config from JSON file. If resolve_password is True, resolve IMAP password from env."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    config_dir = path.parent
    load_dotenv(config_dir / ".env")
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    if not resolve_password:
        return cfg
    imap = cfg.get("imap") or {}
    if imap.get("password") not in (None, ""):
        pass
    elif imap.get("password_env"):
        key = imap["password_env"]
        enc_val = os.environ.get(f"{key}_ENC")
        if enc_val:
            from .env_file import decrypt_env_value
            imap = {**imap, "password": decrypt_env_value(config_dir, enc_val)}
            cfg["imap"] = imap
        else:
            plain_val = os.environ.get(key)
            if not plain_val:
                raise ValueError(
                    f"Environment variable {key} or {key}_ENC is not set (required for IMAP password)"
                )
            imap = {**imap, "password": plain_val}
            cfg["imap"] = imap
    return cfg


def get_config_path() -> Path:
    """Default config path: FETCH2GMAIL_CONFIG or ./config.json."""
    env = os.environ.get("FETCH2GMAIL_CONFIG")
    if env:
        return Path(env)
    return Path.cwd() / "config.json"
