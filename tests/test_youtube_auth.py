from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.function.core import youtube_auth


def test_token_store_roundtrip(tmp_path):
    token_path = tmp_path / "tokens.enc"
    secret_path = tmp_path / "secret.key"
    store = youtube_auth.YouTubeTokenStore(token_path=token_path, secret_path=secret_path)

    payload = {"token": "abc", "refresh_token": "def", "token_uri": "uri"}
    store.save(payload)

    raw = token_path.read_bytes()
    assert raw, "encrypted payload should not be empty"
    assert b"abc" not in raw

    loaded = store.load()
    assert loaded == payload


def test_auth_manager_status_without_client_config(tmp_path):
    store = youtube_auth.YouTubeTokenStore(
        token_path=tmp_path / "tokens.enc",
        secret_path=tmp_path / "secret.key",
    )
    manager = youtube_auth.YouTubeAuthManager(token_store=store, client_config=None)
    status = manager.get_status()
    assert status["status"] == "unconfigured"
    assert status["authenticated"] is False


def test_auth_manager_reads_persisted_credentials(tmp_path):
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    credentials = youtube_auth.google_credentials.Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=list(youtube_auth.DEFAULT_SCOPES),
        expiry=expiry,
    )
    payload = json.loads(credentials.to_json())
    store = youtube_auth.YouTubeTokenStore(
        token_path=tmp_path / "tokens.enc",
        secret_path=tmp_path / "secret.key",
    )
    store.save(payload)

    manager = youtube_auth.YouTubeAuthManager(token_store=store, client_config=None)
    assert manager.has_credentials() is True

    status = manager.get_status()
    assert status["status"] == "authorized"
    assert status["authenticated"] is True

    ensured = manager.ensure_credentials()
    assert ensured.token == "access-token"

