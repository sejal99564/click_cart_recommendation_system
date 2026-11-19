import hashlib
import hmac
import os
import re
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from threading import Lock
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import CollectionItem, Credential, User

ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/")
PRODUCTION = os.getenv("APP_ENV") == "production"
COOKIE = "__Host-shopwise" if PRODUCTION else "shopwise"
if PRODUCTION and not ORIGIN.startswith("https://"):
    raise RuntimeError("FRONTEND_ORIGIN must use HTTPS in production")
SESSION_AGE = 12 * 60 * 60
DB = Annotated[Session, Depends(get_db)]
_attempts: dict[tuple[str, str], int] = {}
_window = -1
_lock = Lock()
_dummy_hash: str


def allowed_frontend_origins() -> list[str]:
    match = re.fullmatch(r"(https?://)(localhost|127\.0\.0\.1)(:\d+)?", ORIGIN)
    if PRODUCTION or os.getenv("APP_ENV", "development") != "development" or not match:
        return [ORIGIN]
    scheme, host, port = match.groups()
    alternate = "127.0.0.1" if host == "localhost" else "localhost"
    return [ORIGIN, f"{scheme}{alternate}{port or ''}"]


def require_origin(request: Request):
    if request.method != "GET" and request.headers.get("origin") not in allowed_frontend_origins():
        raise HTTPException(403, "Invalid request origin")


router = APIRouter(prefix="/api/auth", dependencies=[Depends(require_origin)])


def limit(request: Request, action: str, maximum: int, user_id: int | None = None):
    global _window
    current_window = int(time.monotonic() // 60)
    actor = f"user:{user_id}" if user_id is not None else f"ip:{request.client.host if request.client else ''}"
    key = (actor, action)
    with _lock:
        if current_window != _window:
            _attempts.clear()
            _window = current_window
        if _attempts.get(key, 0) >= maximum or len(_attempts) >= 10000 and key not in _attempts:
            raise HTTPException(429, "Too many requests", headers={"Retry-After": "60"})
        _attempts[key] = _attempts.get(key, 0) + 1


class EmailInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        parts = value.split("@")
        if len(parts) != 2 or not all(parts) or "." not in parts[1] or any(char.isspace() for char in value):
            raise ValueError("Enter a valid email address")
        # Accept a single conventional mailbox, including plus-addressing.
        if any(char in value for char in "<>,;:\"()[]\\") or not value.isascii():
            raise ValueError("Enter a valid email address")
        return value


class ProfileInput(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")


class LoginInput(EmailInput):
    password: str = Field(min_length=1, max_length=128)


class RegisterInput(LoginInput, ProfileInput):
    password: str = Field(min_length=12, max_length=128)


class TokenInput(BaseModel):
    token: str = Field(min_length=43, max_length=43)


class ResetInput(TokenInput):
    password: str = Field(min_length=12, max_length=128)


class PasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)


class ChangeInput(PasswordInput):
    password: str = Field(min_length=12, max_length=128)


class Profile(BaseModel):
    email: str
    name: str
    verified: bool
    role: str


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 * 1024**2)
    return f"{salt.hex()}:{key.hex()}"


_dummy_hash = password_hash(secrets.token_urlsafe(32))


def correct_password(password: str, encoded: str) -> bool:
    salt = bytes.fromhex(encoded.split(":", 1)[0])
    return hmac.compare_digest(password_hash(password, salt), encoded)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(db: Session, user: User, purpose: str, lifetime: int) -> str:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    db.execute(delete(Credential).where(Credential.user_id == user.id, Credential.expires_at <= now))
    db.add(Credential(digest=digest(token), user_id=user.id, purpose=purpose, expires_at=now + lifetime))
    return token


def consume(db: Session, token: str, purpose: str) -> int:
    user_id = db.scalar(delete(Credential).where(
        Credential.digest == digest(token), Credential.purpose == purpose, Credential.expires_at > int(time.time()),
    ).returning(Credential.user_id))
    if user_id is None:
        raise HTTPException(400, "This link is invalid or has expired")
    return user_id


def user_for_update(db: Session, user_id: int | None) -> User:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update()
                     .execution_options(populate_existing=True))
    if user is None:
        raise HTTPException(400, "This credential is no longer valid")
    return user


def redeem(db: Session, token: str, purpose: str) -> User:
    user_id = db.scalar(select(Credential.user_id).where(
        Credential.digest == digest(token), Credential.purpose == purpose, Credential.expires_at > int(time.time()),
    ))
    user = user_for_update(db, user_id)
    consume(db, token, purpose)
    return user


def current_user(request: Request, db: DB) -> User:
    token = request.cookies.get(COOKIE, "")
    if len(token) == 43:
        user = db.scalar(select(User).join(Credential, Credential.user_id == User.id).where(
            Credential.digest == digest(token), Credential.purpose == "session",
            Credential.expires_at > int(time.time()),
        ))
        if user:
            return user
    raise HTTPException(401, "Sign in to continue")


CurrentUser = Annotated[User, Depends(current_user)]


def deliver_password_reset(email: str, token: str):
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise HTTPException(503, "Account email is temporarily unavailable")
    link = f"{ORIGIN}/account/reset#{urlencode({'token': token})}"
    message = EmailMessage()
    message["From"], message["To"] = sender, email
    message["Subject"] = "Reset your Shopwise AI password"
    message.set_content(f"Continue at {link}\n\nIf you did not request this, ignore this email.")
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=8) as smtp:
            if PRODUCTION or os.getenv("SMTP_STARTTLS", "true") == "true":
                smtp.starttls(context=ssl.create_default_context())
            if username := os.getenv("SMTP_USERNAME"):
                smtp.login(username, os.environ["SMTP_PASSWORD"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise HTTPException(503, "Account email is temporarily unavailable") from error


@router.post("/register", status_code=201)
def register(payload: RegisterInput, request: Request, db: DB):
    limit(request, "register", 5)
    user = User(email=payload.email, name=payload.name.strip(), password_hash=password_hash(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == payload.email)) is None:
            raise
        raise HTTPException(409, "This email is already registered. Sign in or reset your password.") from None
    return {"created": True}


@router.post("/login", status_code=204)
def login(payload: LoginInput, request: Request, response: Response, db: DB):
    limit(request, "login", 10)
    user = db.scalar(select(User).where(User.email == payload.email).with_for_update())
    matches = correct_password(payload.password, user.password_hash if user else _dummy_hash)
    if not user or not matches:
        raise HTTPException(401, "Check your email and password")
    previous = request.cookies.get(COOKIE)
    if previous:
        db.execute(delete(Credential).where(Credential.digest == digest(previous), Credential.purpose == "session"))
    token = issue(db, user, "session", SESSION_AGE)
    db.commit()
    response.set_cookie(COOKIE, token, max_age=SESSION_AGE, secure=PRODUCTION, httponly=True, samesite="lax")


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    if token := request.cookies.get(COOKIE):
        db.execute(delete(Credential).where(Credential.digest == digest(token), Credential.purpose == "session"))
        db.commit()
    response.delete_cookie(COOKIE, secure=PRODUCTION, httponly=True, samesite="lax")


@router.post("/forgot", status_code=202)
def forgot(payload: EmailInput, request: Request, db: DB):
    limit(request, "forgot", 5)
    if not os.getenv("SMTP_HOST") or not os.getenv("SMTP_FROM"):
        raise HTTPException(503, "Account email is temporarily unavailable")
    user = db.scalar(select(User).where(User.email == payload.email).with_for_update())
    if user:
        token = issue(db, user, "reset", 1800)
        deliver_password_reset(user.email, token)
        db.commit()
    return {"accepted": True}


@router.post("/reset", status_code=204)
def reset(payload: ResetInput, request: Request, db: DB):
    limit(request, "reset", 10)
    user = redeem(db, payload.token, "reset")
    user.password_hash = password_hash(payload.password)
    db.execute(delete(Credential).where(Credential.user_id == user.id))
    db.commit()


@router.get("/me", response_model=Profile)
def profile(user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.patch("/me", response_model=Profile)
def update_profile(payload: ProfileInput, user: CurrentUser, db: DB):
    user.name = payload.name.strip()
    db.commit()
    return user


@router.post("/password", status_code=204)
def change_password(payload: ChangeInput, request: Request, response: Response, user: CurrentUser, db: DB):
    limit(request, "password", 8, user.id)
    user_for_update(db, user.id)
    user = current_user(request, db)
    if not correct_password(payload.current_password, user.password_hash):
        raise HTTPException(401, "Check your current password")
    user.password_hash = password_hash(payload.password)
    db.execute(delete(Credential).where(Credential.user_id == user.id))
    db.commit()
    response.delete_cookie(COOKIE, secure=PRODUCTION, httponly=True, samesite="lax")


@router.delete("/me", status_code=204)
def delete_account(payload: PasswordInput, request: Request, response: Response, user: CurrentUser, db: DB):
    limit(request, "delete", 8, user.id)
    user_for_update(db, user.id)
    user = current_user(request, db)
    if not correct_password(payload.current_password, user.password_hash):
        raise HTTPException(401, "Check your current password")
    db.execute(delete(Credential).where(Credential.user_id == user.id))
    db.execute(delete(CollectionItem).where(CollectionItem.user_id == user.id))
    db.delete(user)
    db.commit()
    response.delete_cookie(COOKIE, secure=PRODUCTION, httponly=True, samesite="lax")
