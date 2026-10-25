import os
import hmac
import json
import time
import base64
import hashlib
from typing import List, Optional, Dict, Any
from fastapi import Header, HTTPException
from pydantic import BaseModel


class UserCredential(BaseModel):
    user_id: str
    role: str
    allowed_scopes: List[str]
    issuer: str
    expires_at: int


EXPECTED_ISSUER = "senior-platform-auth"
EXPECTED_AUDIENCE = "senior-agent-hub"


def get_jwt_secret() -> str:
    """
    Fail-closed JWT secret retrieval.
    In production environments, AGENT_HUB_JWT_SECRET is mandatory and cannot be empty.
    """
    env = os.environ.get("ENVIRONMENT", "production").lower()
    raw_secret = os.environ.get("AGENT_HUB_JWT_SECRET", "").strip()
    if not raw_secret:
        if env in ("test", "local"):
            return "senior-portfolio-agent-hub-dev-test-key-only"
        raise RuntimeError("CRITICAL: AGENT_HUB_JWT_SECRET must be explicitly set outside test environment")
    return raw_secret


def _b64url_decode(payload: str) -> bytes:
    rem = len(payload) % 4
    if rem > 0:
        payload += "=" * (4 - rem)
    return base64.urlsafe_b64decode(payload)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def create_signed_token(
    user_id: str,
    role: str,
    allowed_scopes: List[str],
    ttl_seconds: int = 3600,
    secret_key: Optional[str] = None,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
    nbf_offset: Optional[int] = None,
    custom_header: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 (HS256) JWT.
    """
    secret = secret_key or get_jwt_secret()
    now = int(time.time())
    header = custom_header or {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "scopes": allowed_scopes,
        "iss": issuer or EXPECTED_ISSUER,
        "aud": audience or EXPECTED_AUDIENCE,
        "iat": now,
        "exp": now + ttl_seconds
    }
    if nbf_offset is not None:
        payload["nbf"] = now + nbf_offset

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    if header.get("alg") == "none":
        signature_b64 = ""
    else:
        signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def authenticate_bearer_token(authorization: Optional[str] = Header(default=None)) -> UserCredential:
    """
    Cryptographic Server-Side Authentication Guard.
    Strictly verifies algorithm (HS256 only), HMAC-SHA256 signature, issuer, audience, nbf, and expiration.
    Rejects any forged, tampered, expired, or missing tokens with HTTP 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication failed: Missing or malformed 'Authorization: Bearer <token>' header"
        )

    raw_token = authorization.split("Bearer ", 1)[1].strip()
    parts = raw_token.split(".")

    if len(parts) != 3:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed: Malformed JWT token structure (must be header.payload.signature)"
        )

    header_b64, payload_b64, signature_b64 = parts

    # 1. Parse and verify header algorithm
    try:
        header_data = json.loads(_b64url_decode(header_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed: Malformed token header")

    if header_data.get("alg") != "HS256":
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: Unsupported or forbidden JWT algorithm '{header_data.get('alg')}'. Only HS256 is permitted."
        )

    # 2. Cryptographic Signature Verification
    secret = get_jwt_secret()
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        provided_sig = _b64url_decode(signature_b64)
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed: Invalid signature encoding")

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise HTTPException(
            status_code=401,
            detail="Authentication failed: Cryptographic signature mismatch. Token is forged or tampered."
        )

    # 3. Parse & Verify Payload Claims
    try:
        payload_data = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed: Malformed token payload")

    # Issuer check
    if payload_data.get("iss") != EXPECTED_ISSUER:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: Untrusted issuer '{payload_data.get('iss')}'. Expected '{EXPECTED_ISSUER}'"
        )

    # Audience check (if present)
    token_aud = payload_data.get("aud")
    if token_aud and token_aud != EXPECTED_AUDIENCE:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: Untrusted audience '{token_aud}'. Expected '{EXPECTED_AUDIENCE}'"
        )

    now = int(time.time())

    # Not before check (nbf)
    nbf = payload_data.get("nbf")
    if nbf is not None and now < nbf:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: Token is not yet valid (nbf: {nbf}, current time: {now})"
        )

    # Expiration check (exp)
    exp = payload_data.get("exp", 0)
    if now > exp:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: Token expired at {exp} (current time: {now})"
        )

    return UserCredential(
        user_id=payload_data.get("sub", "unknown"),
        role=payload_data.get("role", "Operator"),
        allowed_scopes=payload_data.get("scopes", []),
        issuer=payload_data.get("iss"),
        expires_at=exp
    )


def authorize_scope_access(user: UserCredential, requested_scope: str) -> None:
    """
    Authoritative Server-side Scope Guard.
    Ensures that the authenticated user is explicitly allowed to access requested_scope.
    Rejects unauthorized access with HTTP 403.
    """
    if "*" in user.allowed_scopes:
        return

    if requested_scope not in user.allowed_scopes:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: User '{user.user_id}' with role '{user.role}' is not authorized to access scope '{requested_scope}'. Allowed scopes: {user.allowed_scopes}"
        )
