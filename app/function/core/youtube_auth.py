"""OAuth 2.0 ベースの認証フローとトークン管理ユーティリティ。"""

from __future__ import annotations

import base64
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from google.auth import exceptions as google_exceptions
from google.auth.transport.requests import Request
from google.oauth2 import credentials as google_credentials
from app.function.core import paths

LOGGER = logging.getLogger(__name__)

DEFAULT_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)

_SECRET_FILE_NAME = "youtube_credentials.key"
_TOKEN_FILE_NAME = "youtube_credentials.json.enc"
_METADATA_KEY = "__metadata__"


class TokenStoreError(RuntimeError):
    """永続化されたトークンの読み書きに失敗した場合の例外。"""


@dataclass(slots=True)
class _SimpleTokenCipher:
    """BLAKE2b ベースの簡易ストリーム暗号を実装するヘルパー。"""

    key: bytes

    def encrypt(self, payload: bytes) -> bytes:
        iv = secrets.token_bytes(16)
        keystream = self._keystream(len(payload), iv)
        ciphertext = bytes(p ^ k for p, k in zip(payload, keystream))
        mac = self._mac(iv + ciphertext)
        blob = iv + mac + ciphertext
        return base64.urlsafe_b64encode(blob)

    def decrypt(self, payload: bytes) -> bytes:
        try:
            raw = base64.urlsafe_b64decode(payload)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError("Invalid token payload") from exc
        if len(raw) < 16 + 32:
            raise ValueError("Encrypted payload is too short")
        iv = raw[:16]
        mac = raw[16:48]
        ciphertext = raw[48:]
        expected = self._mac(iv + ciphertext)
        if not secrets.compare_digest(mac, expected):
            raise ValueError("Token MAC verification failed")
        keystream = self._keystream(len(ciphertext), iv)
        return bytes(c ^ k for c, k in zip(ciphertext, keystream))

    def _keystream(self, length: int, iv: bytes) -> bytes:
        from hashlib import blake2b

        chunks: list[bytes] = []
        counter = 0
        generated = 0
        while generated < length:
            counter_bytes = counter.to_bytes(4, "big")
            digest = blake2b(self.key + iv + counter_bytes, digest_size=32).digest()
            chunks.append(digest)
            counter += 1
            generated += len(digest)
        stream = b"".join(chunks)
        return stream[:length]

    def _mac(self, payload: bytes) -> bytes:
        from hashlib import blake2s

        return blake2s(self.key + payload, digest_size=32).digest()


class YouTubeTokenStore:
    """YouTube 認証情報を暗号化して永続化するストア。"""

    def __init__(
        self,
        *,
        token_path: Path | None = None,
        secret_path: Path | None = None,
    ) -> None:
        self._token_path = token_path or (paths.config_dir() / _TOKEN_FILE_NAME)
        self._secret_path = secret_path or (paths.config_dir() / _SECRET_FILE_NAME)
        self._cipher: _SimpleTokenCipher | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load(self) -> dict[str, Any] | None:
        if not self._token_path.exists():
            return None
        try:
            encrypted = self._token_path.read_bytes()
        except OSError as exc:  # pragma: no cover - filesystem
            raise TokenStoreError("Failed to read credential store") from exc
        if not encrypted:
            return None
        try:
            cipher = self._ensure_cipher()
            decrypted = cipher.decrypt(encrypted)
        except ValueError:
            LOGGER.warning("Failed to decrypt YouTube credential store; resetting")
            self.clear()
            return None
        try:
            payload = json.loads(decrypted.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Invalid payload detected in credential store; resetting")
            self.clear()
            return None
        if not isinstance(payload, MutableMapping):
            return None
        return dict(payload)

    def save(self, payload: Mapping[str, Any]) -> None:
        serialized = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        cipher = self._ensure_cipher()
        encrypted = cipher.encrypt(serialized)
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._token_path.write_bytes(encrypted)
        except OSError as exc:  # pragma: no cover - filesystem
            raise TokenStoreError("Failed to persist credential store") from exc
        try:
            self._token_path.chmod(0o600)
        except OSError:  # pragma: no cover - best effort permissions
            LOGGER.warning("Failed to adjust credential file permissions", exc_info=True)

    def clear(self) -> None:
        try:
            if self._token_path.exists():
                self._token_path.unlink()
        except OSError:  # pragma: no cover - best effort cleanup
            LOGGER.warning("Failed to remove credential store", exc_info=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_cipher(self) -> _SimpleTokenCipher:
        if self._cipher is None:
            secret = self._load_or_create_secret()
            self._cipher = _SimpleTokenCipher(secret)
        return self._cipher

    def _load_or_create_secret(self) -> bytes:
        self._secret_path.parent.mkdir(parents=True, exist_ok=True)
        if self._secret_path.exists():
            try:
                raw = self._secret_path.read_bytes()
                secret = base64.urlsafe_b64decode(raw)
                if secret:
                    return secret
            except Exception:  # pragma: no cover - defensive
                LOGGER.warning("Invalid credential secret detected; regenerating")
        secret = secrets.token_bytes(32)
        encoded = base64.urlsafe_b64encode(secret)
        try:
            self._secret_path.write_bytes(encoded)
            self._secret_path.chmod(0o600)
        except OSError:  # pragma: no cover - best effort permissions
            LOGGER.warning("Failed to persist credential secret", exc_info=True)
        return secret


class YouTubeAuthManager:
    """OAuth フローとトークンのリフレッシュを司るマネージャー。"""

    def __init__(
        self,
        *,
        token_store: YouTubeTokenStore,
        client_config: Mapping[str, Any] | None = None,
        scopes: Sequence[str] | None = None,
        redirect_port: int | None = None,
    ) -> None:
        self._token_store = token_store
        self._client_config = dict(client_config) if client_config else None
        self._scopes = tuple(scopes or DEFAULT_SCOPES)
        self._redirect_port = redirect_port or 8765

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_browser_flow(self) -> dict[str, Any]:
        if not self._client_config:
            raise ValueError("OAuth クライアント情報が設定されていません")
        LOGGER.info("Starting YouTube OAuth browser flow")
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise ValueError(
                "google-auth-oauthlib パッケージが見つかりません。"
            ) from exc
        flow = InstalledAppFlow.from_client_config(
            self._client_config,
            scopes=self._scopes,
        )
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=self._redirect_port,
            authorization_prompt_message="Google アカウントで認証を行ってください。",
            success_message="認証が完了しました。このウィンドウを閉じてください。",
            open_browser=True,
        )
        self._persist_credentials(credentials)
        return self.get_status()

    def ensure_credentials(self) -> google_credentials.Credentials:
        payload = self._token_store.load()
        if not payload:
            raise ValueError("YouTube 認証が完了していません")
        try:
            credentials = self._credentials_from_payload(payload)
        except ValueError as exc:
            LOGGER.warning("Failed to parse stored YouTube credentials; clearing", exc_info=exc)
            self._token_store.clear()
            raise ValueError("保存された YouTube 認証情報が壊れています。再認証してください") from exc
        if credentials.valid:
            return credentials
        if not credentials.refresh_token:
            raise ValueError("YouTube 認証情報が無効です。再度認証してください")
        try:
            credentials.refresh(Request())
        except google_exceptions.RefreshError as exc:
            LOGGER.error("Failed to refresh YouTube access token", exc_info=exc)
            self._token_store.clear()
            raise ValueError("YouTube 認証トークンの更新に失敗しました") from exc
        self._persist_credentials(credentials)
        return credentials

    def has_credentials(self) -> bool:
        payload = self._token_store.load()
        if not payload:
            return False
        try:
            credentials = self._credentials_from_payload(payload)
        except ValueError:
            LOGGER.warning("Invalid YouTube credential payload detected; clearing store")
            self._token_store.clear()
            return False
        if credentials.valid:
            return True
        return bool(credentials.refresh_token)

    def has_client_config(self) -> bool:
        return self._client_config is not None

    def get_status(self) -> dict[str, Any]:
        payload = self._token_store.load()
        if not payload:
            if not self._client_config:
                return {
                    "status": "unconfigured",
                    "authenticated": False,
                    "message": "OAuth クライアント情報が設定されていません",
                    "scopes": list(self._scopes),
                }
            return {
                "status": "unauthorized",
                "authenticated": False,
                "message": "Google アカウントがまだ認証されていません",
                "scopes": list(self._scopes),
            }

        try:
            credentials = self._credentials_from_payload(payload)
        except ValueError:
            LOGGER.warning("Stored YouTube credentials are invalid; requesting re-authentication")
            self._token_store.clear()
            return {
                "status": "invalid",
                "authenticated": False,
                "message": "保存された認証情報を読み取れませんでした。再認証してください",
                "scopes": list(self._scopes),
            }
        now = datetime.now(timezone.utc)
        expiry = credentials.expiry
        expires_at_iso: str | None = None
        expires_in: int | None = None
        if expiry is not None:
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            else:
                expiry = expiry.astimezone(timezone.utc)
            expires_at_iso = expiry.isoformat()
            expires_in = int((expiry - now).total_seconds())
        metadata = self._metadata_from_payload(payload)
        updated_at = metadata.get("updated_at") if metadata else None
        if updated_at:
            try:
                # Validate timestamp format but keep original
                datetime.fromisoformat(updated_at)
            except ValueError:
                updated_at = None

        status = "authorized"
        authenticated = True
        message = "Google アカウントの認証が完了しています"
        if credentials.expired and credentials.refresh_token:
            status = "expired"
            message = "アクセストークンの有効期限が切れています。自動更新を待機中です"
        elif not credentials.valid and not credentials.refresh_token:
            status = "invalid"
            authenticated = False
            message = "認証情報が無効です。再度認証してください"

        return {
            "status": status,
            "authenticated": authenticated,
            "expires_at": expires_at_iso,
            "expires_in": expires_in,
            "updated_at": updated_at,
            "scopes": list(self._scopes),
            "message": message,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _credentials_from_payload(
        self, payload: Mapping[str, Any]
    ) -> google_credentials.Credentials:
        info = {k: v for k, v in payload.items() if k != _METADATA_KEY}
        return google_credentials.Credentials.from_authorized_user_info(
            info,
            scopes=self._scopes,
        )

    def _persist_credentials(self, credentials: google_credentials.Credentials) -> None:
        payload = json.loads(credentials.to_json())
        payload[_METADATA_KEY] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stored_at_epoch": int(time.time()),
        }
        self._token_store.save(payload)

    @staticmethod
    def _metadata_from_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        data = payload.get(_METADATA_KEY)
        if isinstance(data, Mapping):
            return data
        return {}


def resolve_redirect_port(settings: Mapping[str, Any], default: int = 8765) -> int:
    raw = settings.get("oauth_redirect_port") if isinstance(settings, Mapping) else None
    if raw in (None, ""):
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def load_client_config(settings: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """設定辞書から OAuth クライアント情報を読み込みます。"""

    if not isinstance(settings, Mapping):
        return None

    path_value = settings.get("client_secret_path") or settings.get(
        "client_secrets_path"
    )
    if path_value:
        path = Path(str(path_value)).expanduser()
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                LOGGER.warning("Invalid OAuth client file detected: %s", path)
            else:
                if isinstance(data, Mapping) and ("installed" in data or "web" in data):
                    return data

    client_id = str(settings.get("client_id", "") or "").strip()
    client_secret = str(settings.get("client_secret", "") or "").strip()
    if client_id and client_secret:
        redirect_uris = settings.get("redirect_uris")
        if isinstance(redirect_uris, str):
            redirect_list = [
                uri.strip()
                for uri in redirect_uris.split(",")
                if uri.strip()
            ]
        elif isinstance(redirect_uris, Sequence):
            redirect_list = [str(uri).strip() for uri in redirect_uris if str(uri).strip()]
        else:
            redirect_list = []
        if not redirect_list:
            redirect_list = [f"http://127.0.0.1:{resolve_redirect_port(settings)}"]
        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": redirect_list,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
    return None


__all__ = [
    "DEFAULT_SCOPES",
    "TokenStoreError",
    "YouTubeAuthManager",
    "YouTubeTokenStore",
    "load_client_config",
    "resolve_redirect_port",
]

