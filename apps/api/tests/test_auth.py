import time

import jwt

from app.auth import decode_token
from app.config import get_settings


def test_decode_token_local_secret(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(settings, "jwt_local_secret", "test-secret")
    token = jwt.encode({"sub": "user1", "exp": int(time.time()) + 60}, "test-secret", algorithm="HS256")
    claims = decode_token(token)
    assert claims["sub"] == "user1"
