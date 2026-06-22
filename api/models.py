"""
AgriSaathi — API Request/Response Models
==========================================
WHY: Pydantic models enforce type safety and PII protection at the data layer.
Every model's __repr__ masks sensitive fields, preventing accidental PII leaks
in logs even if a developer writes `logger.debug(f"request: {req}")`.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Language(str, Enum):
    """Supported languages for AgriSaathi."""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    MARATHI = "mr"


class AgentType(str, Enum):
    """Agent identifiers for routing and audit."""
    CONCIERGE = "farmer_concierge"
    CROP_DOCTOR = "crop_doctor"
    WEATHER = "weather_advisor"
    MARKET = "market_whisperer"
    SCHEME = "scheme_guide"


# ---------------------------------------------------------------------------
# PII-safe base model
# ---------------------------------------------------------------------------
class PIISafeModel(BaseModel):
    """Base model that masks PII in string representations.

    WHY: Even with middleware PII redaction, a developer might log a model
    instance directly. This defense-in-depth approach masks Aadhaar and
    phone numbers in __repr__ and __str__ so PII never hits log files.
    """

    def __repr__(self) -> str:
        raw = super().__repr__()
        return _mask_pii(raw)

    def __str__(self) -> str:
        raw = super().__str__()
        return _mask_pii(raw)


def _mask_pii(text: str) -> str:
    """Mask Aadhaar numbers and Indian phone numbers in text.

    Aadhaar: 12 digits, with or without spaces/hyphens → XXXX-XXXX-1234
    Phone: +91 followed by 10 digits → +91-XXXXX-XX789
    """
    # Aadhaar: various formats (1234 5678 9012, 1234-5678-9012, 123456789012)
    text = re.sub(
        r'\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b',
        r'XXXX-XXXX-\3',
        text,
    )
    # Indian phone: +91XXXXXXXXXX or 91XXXXXXXXXX or 0XXXXXXXXXX
    text = re.sub(
        r'(\+?91|0)[\s-]?(\d{5})[\s-]?(\d{5})',
        r'\1-XXXXX-XX\3',
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class ChatRequest(PIISafeModel):
    """Incoming chat message from the farmer.

    WHY: Single entry point for all text interactions. The message field
    carries the farmer's question in any supported language. session_id
    enables cross-visit memory.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Farmer's message in any supported language",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Session ID for conversation continuity across visits",
    )
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Authenticated user identifier (from JWT)",
    )
    language: Language = Field(
        default=Language.HINDI,
        description="Preferred language (auto-detected if not specified)",
    )


class DiagnoseRequest(PIISafeModel):
    """Crop disease diagnosis request with photo.

    WHY: Separate from ChatRequest because it carries binary image data.
    image_base64 contains the leaf photo; image_filename is used in mock
    mode to match PlantVillage ground truth.
    """
    image_base64: str = Field(
        ...,
        min_length=100,
        description="Base64-encoded crop leaf photo (JPEG/PNG)",
    )
    image_filename: str | None = Field(
        default=None,
        description="Original filename (used in mock mode for PlantVillage eval)",
    )
    session_id: str = Field(..., min_length=1, max_length=128)
    user_id: str = Field(..., min_length=1, max_length=128)
    language: Language = Field(default=Language.HINDI)


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------
class ChatResponse(PIISafeModel):
    """Agent response to the farmer."""
    response: str = Field(
        ...,
        description="Agent's response in the farmer's language",
    )
    agent_used: AgentType = Field(
        ...,
        description="Which agent handled this request",
    )
    session_id: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (confidence scores, tool outputs, etc.)",
    )


class CropDiagnosisResponse(PIISafeModel):
    """Structured crop disease diagnosis result."""
    disease: str = Field(..., description="Identified disease name")
    confidence: float = Field(..., ge=0.0, le=1.0)
    crop_name: str = Field(..., description="Identified crop species")
    treatment: str = Field(..., description="Recommended treatment")
    organic_alternative: bool = Field(
        ...,
        description="Whether an organic treatment option exists",
    )
    organic_treatment: str | None = Field(
        default=None,
        description="Organic treatment details (if available)",
    )
    severity: str = Field(..., description="low / medium / high / critical")
    agent_used: AgentType = Field(default=AgentType.CROP_DOCTOR)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    agents_loaded: int = 5
    mcp_servers: int = 3
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    detail: str | None = None
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
