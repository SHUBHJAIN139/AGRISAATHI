"""
AgriSaathi — WhatsApp Webhook Route (Scaffolded)
==================================================
WHY: 500M+ Indians use WhatsApp. For a low-literacy farmer, WhatsApp is
more familiar than a PWA. This route scaffolds the webhook integration
point for WhatsApp Cloud API, but returns 501 until Meta Business
verification is completed.

Production deploy requires:
1. Meta Business account verification
2. WhatsApp Business API access
3. Webhook verification token in Secret Manager
4. Message template approval for outbound messages
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/webhooks", tags=["whatsapp"])


@router.get("/whatsapp")
async def whatsapp_verify(request: Request) -> JSONResponse:
    """WhatsApp webhook verification endpoint.

    WHY: Meta sends a GET request with a challenge token during webhook
    setup. This endpoint must echo the challenge to complete registration.
    Currently returns 501 since we haven't completed Meta Business verification.
    """
    return JSONResponse(
        status_code=501,
        content={
            "status": "scaffolded",
            "note": "Production deploy requires Meta Business verification. "
                    "See docs/ARCHITECTURE.md for WhatsApp integration guide.",
        },
    )


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> JSONResponse:
    """WhatsApp incoming message webhook.

    WHY: Receives farmer messages from WhatsApp Cloud API, routes them
    through FarmerConcierge, and sends the response back via WhatsApp.
    Currently returns 501 — scaffolded for future implementation.

    Production flow:
    1. Verify webhook signature (X-Hub-Signature-256 header)
    2. Parse incoming message (text, image, voice)
    3. Route through FarmerConcierge agent
    4. Send response back via WhatsApp Cloud API
    5. Log to audit trail
    """
    return JSONResponse(
        status_code=501,
        content={
            "status": "scaffolded",
            "note": "Production deploy requires Meta Business verification. "
                    "Incoming messages will be routed through FarmerConcierge "
                    "once WhatsApp Cloud API integration is complete.",
        },
    )
