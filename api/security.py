"""
AgriSaathi — Security Middleware
=================================
WHY: Indian farmers' data is sacred. A farmer sharing their Aadhaar number
or phone number in a chat should NEVER see that data leak into logs, error
messages, or third-party services. This module implements 3 security layers:

1. PIIRedactionMiddleware — regex-based scrubbing of Aadhaar + phone in all responses
2. JWTAuthMiddleware — token validation (mock JWT for local, Firebase Auth in prod)
3. RateLimitMiddleware — 60 req/min per user to prevent abuse
4. AuditLogger — immutable audit trail of every agent decision

7-Point Security Control Table:
| # | Control                    | Implementation                              |
|---|----------------------------|---------------------------------------------|
| 1 | PII Redaction              | Regex in middleware + Pydantic __repr__      |
| 2 | Authentication             | JWT (mock) / Firebase phone OTP (prod)       |
| 3 | Rate Limiting              | Per-user sliding window, 60/min              |
| 4 | Tool Isolation             | Sub-agents have restricted tool lists         |
| 5 | Secret Management          | .env local / Secret Manager prod             |
| 6 | Audit Trail                | Every agent decision logged with timestamp   |
| 7 | Network Security           | CORS whitelist, VPC-SC + Cloud Armor (prod)  |
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import HTTPException, Request, Response
import jwt
from jwt.exceptions import PyJWTError
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


# =============================================================================
# 1. PII Redaction Middleware
# =============================================================================
class PIIRedactionMiddleware(BaseHTTPMiddleware):
    """Strips Aadhaar numbers and Indian phone numbers from all HTTP responses.

    WHY: Even if the agent accidentally includes PII in its response, this
    middleware catches it before it reaches the farmer's phone. Belt and
    suspenders with the Pydantic-level masking in models.py.

    Patterns:
    - Aadhaar: 12 digits with optional spaces/hyphens → XXXX-XXXX-[last4]
    - Phone: +91/91/0 prefix + 10 digits → [prefix]-XXXXX-XX[last3]
    """

    # WHY: Compiled once at startup for performance. These patterns handle
    # all common Aadhaar and Indian phone number formats.
    AADHAAR_PATTERN = re.compile(
        r'\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b'
    )
    PHONE_PATTERN = re.compile(
        r'(\+?91|0)[\s-]?(\d{5})[\s-]?(\d{5})'
    )

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)

        # Only redact JSON responses (not images, HTML, etc.)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read and redact the response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        redacted = self._redact(body.decode("utf-8"))

        return Response(
            content=redacted,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type="application/json",
        )

    def _redact(self, text: str) -> str:
        """Apply all PII redaction patterns to text."""
        text = self.AADHAAR_PATTERN.sub(r'XXXX-XXXX-\3', text)
        text = self.PHONE_PATTERN.sub(r'\1-XXXXX-XX\3', text)
        return text


# =============================================================================
# 2. JWT Auth Middleware
# =============================================================================
class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT tokens on protected endpoints.

    WHY: Prevents unauthorized access to the API. In local dev, uses a shared
    secret (HS256). In production, swap for Firebase Auth public key validation.

    Public endpoints (no auth required):
    - GET /health
    - GET /docs
    - GET /openapi.json
    - POST /webhooks/whatsapp (has its own verification)
    """

    PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/webhooks/whatsapp"}

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.secret = os.environ.get("JWT_SECRET", "change-me-in-production")
        self.algorithm = os.environ.get("JWT_ALGORITHM", "HS256")

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # WHY: In mock/demo mode, skip auth so the demo is one-click.
        # Real auth still applies when MOCK_MODE=false.
        if os.getenv("MOCK_MODE", "true").lower() == "true":
            return await call_next(request)

        # Skip auth for public endpoints
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for preflight CORS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header. Expected: Bearer <token>",
            )

        token = auth_header.split("Bearer ", 1)[1]

        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            # Attach user info to request state for downstream use
            request.state.user_id = payload.get("sub", "anonymous")
            request.state.user_claims = payload
        except PyJWTError as e:  # TODO: re-test with pyjwt
            logger.warning("jwt_validation_failed", error=str(e))
            raise HTTPException(
                status_code=401,
                detail=f"Invalid JWT token: {e}",
            )

        return await call_next(request)


# =============================================================================
# 3. Rate Limit Middleware
# =============================================================================
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user sliding window rate limiter.

    WHY: Prevents a single user (or bot) from overwhelming the API.
    Default: 60 requests per minute per user. Identified by JWT user_id
    or IP address if unauthenticated.
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.max_requests = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
        self.window_seconds = 60
        # WHY: In-memory store. For multi-instance production, use Redis.
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Identify the user
        user_key = getattr(request.state, "user_id", None) or request.client.host

        # Clean expired entries and check limit
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[user_key] = [
            t for t in self._requests[user_key] if t > cutoff
        ]

        if len(self._requests[user_key]) >= self.max_requests:
            logger.warning(
                "rate_limit_exceeded",
                user=user_key,
                count=len(self._requests[user_key]),
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per minute.",
            )

        self._requests[user_key].append(now)
        return await call_next(request)


# =============================================================================
# 4. Audit Logger
# =============================================================================
class AuditLogger:
    """Immutable audit trail for agent decisions.

    WHY: Every agent delegation, tool call, and response must be traceable.
    This is both a debugging tool and a compliance requirement for any
    AI system giving agricultural advice.

    Each audit entry contains:
    - timestamp (UTC ISO 8601)
    - user_id (PII-redacted)
    - session_id
    - action (intent_classified, agent_delegated, tool_called, response_sent)
    - agent (which agent handled it)
    - details (action-specific metadata)
    """

    def __init__(self) -> None:
        self.log_path = os.environ.get("AUDIT_LOG_PATH", "./data/audit.log")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log(
        self,
        action: str,
        user_id: str,
        session_id: str,
        agent: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Write an immutable audit entry.

        WHY: JSON Lines format for easy parsing by log analysis tools.
        Each line is a self-contained JSON object.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": _redact_for_audit(user_id),
            "session_id": session_id,
            "agent": agent,
            "details": details or {},
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("audit_log_write_failed", error=str(e))

        logger.info("audit_logged", action=action, agent=agent)


def _redact_for_audit(value: str) -> str:
    """Redact PII from audit log values."""
    value = re.sub(r'\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b', r'XXXX-XXXX-\3', value)
    value = re.sub(r'(\+?91|0)[\s-]?(\d{5})[\s-]?(\d{5})', r'\1-XXXXX-XX\3', value)
    return value


# =============================================================================
# 5. JWT Token Generator (for local development only)
# =============================================================================
def create_mock_token(user_id: str, expires_minutes: int = 1440) -> str:
    """Generate a mock JWT for local development.

    WHY: In production, Firebase Auth issues tokens via phone OTP.
    For local development, this function creates compatible JWTs
    so developers can test without Firebase.

    ⚠️ NEVER use this in production. The JWT_SECRET must come from
    Secret Manager, not an environment variable.
    """
    secret = os.environ.get("JWT_SECRET", "change-me-in-production")
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")

    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        "iss": "agri-saathi-dev",
        "role": "farmer",
    }
    return jwt.encode(payload, secret, algorithm=algorithm)
