"""Encryption for workspace-scoped provider credentials."""
import base64
import hashlib
import json
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


def _cipher() -> Fernet:
    key = settings.INTEGRATION_ENCRYPTION_KEY
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()).decode()
    return Fernet(key.encode())


def seal(value: dict) -> dict:
    return {"_ciphertext": _cipher().encrypt(json.dumps(value).encode()).decode()}


def unseal(value: dict | None) -> dict:
    if not value:
        return {}
    token = value.get("_ciphertext") if isinstance(value, dict) else None
    if not token:
        return value  # legacy development data
    try:
        return json.loads(_cipher().decrypt(token.encode()).decode())
    except (InvalidToken, ValueError, json.JSONDecodeError):
        return {}
