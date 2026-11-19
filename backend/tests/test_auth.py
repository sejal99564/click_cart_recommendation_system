from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth
from app.main import app
from app.models import Credential, User


def test_loopback_alias_allows_registration_and_login(monkeypatch):
    monkeypatch.setattr(auth, "ORIGIN", "http://localhost:3000")
    monkeypatch.setattr(auth, "PRODUCTION", False)
    monkeypatch.setenv("APP_ENV", "development")
    credentials = {"email": "loopback@example.test", "password": "loopback-test-password"}
    with TestClient(app, headers={"Origin": "http://127.0.0.1:3000"}) as client:
        signup = client.post("/api/auth/register", json={**credentials, "name": "Loopback Test"})
        assert signup.status_code == 201
        assert client.post("/api/auth/login", json=credentials).status_code == 204
        assert client.get("/api/auth/me").json()["email"] == credentials["email"]
        for origin in ("http://127.0.0.1:3001", "http://localhost.example.test:3000"):
            assert client.post("/api/auth/login", headers={"Origin": origin}, json=credentials).status_code == 403
        monkeypatch.setattr(auth, "PRODUCTION", True)
        assert client.post("/api/auth/login", json=credentials).status_code == 403


def test_account_lifecycle(monkeypatch, migrated_database):
    delivered = {}
    monkeypatch.setenv("SMTP_HOST", "example.test")
    monkeypatch.setenv("SMTP_FROM", "shopwise@example.test")
    monkeypatch.setattr(auth, "deliver_password_reset", lambda email, token: delivered.update(reset=token))
    credentials = {"email": "shopper@example.test", "password": "initial-password-123"}
    replacement = "replacement-password-456"
    registration = {**credentials, "name": "Shopper"}
    with TestClient(app, headers={"Origin": auth.ORIGIN}) as client:
        assert client.get("/api/auth/me").status_code == 401
        malformed = client.post("/api/auth/register", json={**registration, "password": "too-short"})
        assert malformed.status_code == 422 and "too-short" not in malformed.text
        assert client.post("/api/auth/register", headers={"Origin": "https://elsewhere.test"}, json=registration).status_code == 403
        with monkeypatch.context() as no_mail:
            no_mail.delenv("SMTP_HOST")
            no_mail.delenv("SMTP_FROM")
            assert client.post("/api/auth/register", json=registration).status_code == 201
            assert client.post("/api/auth/register", json=registration).status_code == 409
        assert delivered == {}
        login = client.post("/api/auth/login", json=credentials)
        assert login.status_code == 204 and "HttpOnly" in login.headers["set-cookie"]
        assert client.get("/api/auth/me").json()["name"] == "Shopper"
        assert client.patch("/api/auth/me", json={"name": "Updated", "role": "admin"}).json()["role"] == "customer"
        raw_session = client.cookies.get(auth.COOKIE)
        with Session(migrated_database) as db:
            assert db.scalar(select(User)).password_hash != credentials["password"]
            assert db.get(Credential, raw_session) is None
            assert db.get(Credential, auth.digest(raw_session)) is not None
        assert client.post("/api/auth/forgot", json={"email": credentials["email"]}).status_code == 202
        reset = {"token": delivered["reset"], "password": replacement}
        assert client.post("/api/auth/reset", json=reset).status_code == 204
        assert client.post("/api/auth/reset", json=reset).status_code == 400
        assert client.get("/api/auth/me").status_code == 401
        assert client.post("/api/auth/login", json=credentials).status_code == 401
        assert client.post("/api/auth/login", json={**credentials, "password": replacement}).status_code == 204
        assert client.post("/api/auth/password", json={"current_password": replacement, "password": credentials["password"]}).status_code == 204
        assert client.get("/api/auth/me").status_code == 401
        assert client.post("/api/auth/login", json=credentials).status_code == 204
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/auth/me").status_code == 401
        assert client.post("/api/auth/login", json=credentials).status_code == 204
        assert client.request("DELETE", "/api/auth/me", json={"current_password": credentials["password"]}).status_code == 204
        assert client.get("/api/auth/me").status_code == 401
        with Session(migrated_database) as db:
            assert db.scalar(select(User)) is None
            assert db.scalar(select(Credential)) is None
