import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.core.secrets import seal, unseal
from app.routers.webhooks import _verify_razorpay_signature
import hashlib
import hmac


def test_secrets_round_trip():
    payload = {"key_secret": "private", "sender_email": "ops@example.com"}
    encrypted = seal(payload)
    assert encrypted != payload
    assert unseal(encrypted) == payload


def test_razorpay_signature_validation():
    body, secret = b'{"event":"payment.failed"}', "whsec_test"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert _verify_razorpay_signature(body, signature, secret)
    assert not _verify_razorpay_signature(body, "wrong", secret)
