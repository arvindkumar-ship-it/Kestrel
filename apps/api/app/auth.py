import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from app.config import get_settings

settings = get_settings()
_jwks_client: PyJWKClient | None = None


class Principal:
    def __init__(self, subject: str, tenant_id: str, roles: list[str], claims: dict) -> None:
        self.subject = subject
        self.tenant_id = tenant_id
        self.roles = roles
        self.claims = claims


def _decode_via_jwks(token: str) -> dict:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.jwt_jwks_url)
    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.jwt_audience or None,
        issuer=settings.jwt_issuer or None,
        options={"require": ["exp", "sub"]},
    )


def _decode_via_shared_secret(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_local_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience or None,
        issuer=settings.jwt_issuer or None,
        options={"require": ["exp", "sub"]},
    )


def decode_token(token: str) -> dict:
    """RS256 via JWKS in staging/production; HS256 shared-secret fallback in local/test
    so the API is exercisable without standing up a real identity provider."""
    if settings.app_env in ("local", "test") and settings.jwt_local_secret:
        return _decode_via_shared_secret(token)
    if not settings.jwt_jwks_url:
        raise RuntimeError("jwt_jwks_url is not configured")
    return _decode_via_jwks(token)


async def get_current_principal(request: Request) -> Principal:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = auth_header[7:]
    try:
        claims = decode_token(token)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

    return Principal(
        subject=claims["sub"],
        tenant_id=claims.get("tenant_id", claims["sub"]),
        roles=claims.get("roles", []),
        claims=claims,
    )
