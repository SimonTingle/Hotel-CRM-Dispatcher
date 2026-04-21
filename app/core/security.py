import hashlib
import hmac

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def verify_hmac_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    received = signature_header[len("sha256="):]
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received, expected)


async def require_hmac(request: Request, settings: Settings = Depends(get_settings)) -> None:
    body = await request.body()
    # Cache raw body so the route handler can still parse it
    request.state.raw_body = body
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_hmac_signature(body, sig, settings.wa_app_secret.get_secret_value()):
        raise HTTPException(status_code=403, detail="Invalid signature")


async def get_admin_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if not hmac.compare_digest(
        credentials.credentials,
        settings.admin_api_key.get_secret_value(),
    ):
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return credentials.credentials
