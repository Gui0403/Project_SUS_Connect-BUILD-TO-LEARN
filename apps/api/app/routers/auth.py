import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import authenticated_user
from app.models import RefreshToken, User
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from app.security import (
    burn_password_check,
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    utcnow,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _issue_tokens(
    db: Session, user: User, family_id: uuid.UUID
) -> tuple[TokenResponse, RefreshToken]:
    refresh = new_refresh_token()
    row = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_refresh_token(refresh),
        family_id=family_id,
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(row)
    tokens = TokenResponse(
        access_token=create_access_token(user.id, user.role), refresh_token=refresh
    )
    return tokens, row


def _revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    now = utcnow()
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))

    if user is None:
        burn_password_check()
        raise _invalid_credentials()

    if user.locked_until is not None and user.locked_until > now:
        burn_password_check()
        raise _invalid_credentials()

    if not user.active or not verify_password(body.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
        db.commit()
        raise _invalid_credentials()

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    tokens, _ = _issue_tokens(db, user, family_id=uuid.uuid4())
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    if row is None:
        raise _invalid_credentials()

    if row.revoked_at is not None:
        # Token já usado/revogado sendo reapresentado: sinal de roubo. Revoga a família inteira.
        _revoke_family(db, row.family_id)
        db.commit()
        raise _invalid_credentials()

    if row.expires_at <= utcnow():
        raise _invalid_credentials()

    user = db.get(User, row.user_id)
    if user is None or not user.active:
        raise _invalid_credentials()

    tokens, new_row = _issue_tokens(db, user, family_id=row.family_id)
    row.revoked_at = utcnow()
    row.replaced_by_id = new_row.id
    db.commit()
    return tokens


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    body: LogoutRequest,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token),
            RefreshToken.user_id == user.id,
        )
    )
    if row is not None:
        _revoke_family(db, row.family_id)
        db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(authenticated_user)):
    return user


@router.post("/change-password", status_code=204, response_class=Response)
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid current password")
    if body.new_password.lower() == user.email:
        raise HTTPException(status_code=422, detail="Password must differ from email")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()
    return Response(status_code=204)