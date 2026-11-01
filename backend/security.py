import secrets
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models import User

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash('constant-time-nonexistent-account-check')
# Ephemeral development secret invalidates sessions on restart; production must configure JWT_SECRET.
SECRET = settings.jwt_secret or secrets.token_urlsafe(48)
bearer = HTTPBearer(auto_error=False)
COOKIE_NAME = 'traceback_session'


def set_session(response: Response, user):
    response.set_cookie(
        COOKIE_NAME,
        token(user),
        max_age=8 * 3600,
        httponly=True,
        secure=settings.environment == 'production',
        samesite='lax',
        path='/',
    )


def clear_session(response: Response):
    response.delete_cookie(
        COOKIE_NAME,
        path='/',
        httponly=True,
        secure=settings.environment == 'production',
        samesite='lax',
    )


def token(user):
    return jwt.encode(
        {
            'sub': str(user.id),
            'ver': user.token_version,
            'iss': 'traceback-ai',
            'aud': 'traceback-web',
            'exp': datetime.now(timezone.utc) + timedelta(hours=8),
        },
        SECRET,
        algorithm='HS256',
    )


def current_user(
    request: Request,
    auth: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        raw = auth.credentials if auth else request.cookies.get(COOKIE_NAME)
        if not raw:
            raise ValueError()
        payload = jwt.decode(
            raw,
            SECRET,
            algorithms=['HS256'],
            issuer='traceback-ai',
            audience='traceback-web',
            options={'require': ['exp', 'sub', 'ver']},
        )
        user = db.get(User, int(payload['sub']))
        if not user or payload['ver'] != user.token_version:
            raise ValueError()
        return user
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Invalid or expired session')


def reviewer(user: User = Depends(current_user)):
    if user.role not in ('admin', 'reviewer'):
        raise HTTPException(403, 'Reviewer permission required')
    return user
