"""JWT login and principal endpoints."""

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db.models import AuditLog, User
from app.schemas.auth import LoginRequest, Principal, TokenResponse
from app.security.auth import (
    TOKEN_LIFETIME_MINUTES,
    create_access_token,
    decode_access_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
ALLOWED_ROLES = {"ADMIN", "FLEET_MANAGER", "ANALYST", "VIEWER"}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    role = user.role.upper()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Account role is not authorized")
    token = create_access_token(str(user.id), user.email, str(user.fleet_id), role)
    db.add(AuditLog(fleet_id=user.fleet_id, user_id=user.id, action="login",
                    entity_type="user", entity_id=str(user.id), succeeded=True))
    db.commit()
    return TokenResponse(access_token=token, expires_in=TOKEN_LIFETIME_MINUTES * 60)


def get_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = decode_access_token(credentials.credentials)
        role = str(claims["role"]).upper()
        if role not in ALLOWED_ROLES:
            raise ValueError("invalid role")
        return Principal(user_id=claims["sub"], email=claims["email"],
                         fleet_id=claims["fleet_id"], role=role)
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token",
                            headers={"WWW-Authenticate": "Bearer"}) from exc


def require_roles(*allowed: str):
    allowed_roles = {role.upper() for role in allowed}

    def check_role(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role for this action")
        return principal

    return check_role


@router.get("/me", response_model=Principal)
def me(principal: Principal = Depends(get_principal)) -> Principal:
    return principal
