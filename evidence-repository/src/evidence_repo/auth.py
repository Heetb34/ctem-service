import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import get_settings
from .logging import log
from .schemas import RoleClaim

_bearer = HTTPBearer(auto_error=False)

class Principal:
    def __init__(self, tenant_id: uuid.UUID, user_id: uuid.UUID, roles: list[str]):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.roles = roles

    def has_any(self, allowed: list[str]) -> bool:
        return any(r in self.roles for r in allowed)

async def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    s = get_settings()
    try:
        claims = jwt.decode(creds.credentials, s.jwt_secret, algorithms=[s.jwt_alg])
        return Principal(
            tenant_id=uuid.UUID(claims["tenant_id"]),
            user_id=uuid.UUID(claims["user_id"]),
            roles=list(claims.get("roles", [])),
        )
    except (JWTError, KeyError, ValueError) as e:
        log.warning("jwt_invalid", error=str(e))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from e

def require_roles(*allowed: RoleClaim):
    async def _dep(p: Principal = Depends(get_principal)) -> Principal:
        if not p.has_any(list(allowed)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return p

    return _dep

# Dev-only helper for smoke testing; never mounted as an endpoint.
def mint_dev_token(tenant_id: str, user_id: str, roles: list[str] | None = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "roles": roles or ["evidence_writer", "evidence_reader", "auditor"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_alg)
