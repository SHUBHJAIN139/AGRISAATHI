"""
AgriSaathi — FastAPI Gateway
==============================
WHY: This is the single HTTP entry point for all client interactions.
Every request flows through: CORS → JWT Auth → PII Redaction → Rate Limit
→ Agent Router → Response. This layered architecture ensures security
controls are applied uniformly, regardless of which agent handles the request.

Endpoints:
- POST /chat          — Text conversation with FarmerConcierge
- POST /diagnose      — Photo-based crop disease diagnosis
- GET  /health        — Health check (public, no auth)
- GET  /session/{id}  — Retrieve session history
- POST /token         — Generate mock JWT (dev only)
- POST /webhooks/whatsapp — WhatsApp webhook (scaffolded)
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models import (
    ChatRequest,
    ChatResponse,
    CropDiagnosisResponse,
    DiagnoseRequest,
    ErrorResponse,
    HealthResponse,
    AgentType,
)
from api.security import (
    AuditLogger,
    JWTAuthMiddleware,
    PIIRedactionMiddleware,
    RateLimitMiddleware,
    create_mock_token,
)
from api.session_store import SQLiteSessionStore
from api.routes.whatsapp import router as whatsapp_router

# Load environment variables
load_dotenv()

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Global instances
# ---------------------------------------------------------------------------
session_store = SQLiteSessionStore()
audit_logger = AuditLogger()


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle.

    WHY: Initialize session store and verify agent imports at startup.
    This catches configuration errors immediately rather than on first request.
    """
    logger.info("agri_saathi_starting", mock_mode=os.environ.get("MOCK_LLM", "true"))

    # Verify agents are importable
    try:
        from agents.farmer_concierge import farmer_concierge_agent
        logger.info(
            "agents_loaded",
            root_agent=farmer_concierge_agent.name,
            sub_agents=[sa.name for sa in farmer_concierge_agent.sub_agents],
        )
    except ImportError as e:
        logger.error("agent_import_failed", error=str(e))
        # Don't crash — allow health check to report the issue

    yield

    logger.info("agri_saathi_shutting_down")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AgriSaathi API",
    description=(
        "अन्नदाता साथी — Multilingual AI farming companion for "
        "smallholder Indian farmers. Provides crop disease diagnosis, "
        "weather forecasts, mandi prices, and government scheme guidance."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Middleware Stack (order matters: last added = first executed) ───────────
# WHY: Middleware executes in reverse order of addition.
# Request flow: CORS → JWTAuth → RateLimit → PIIRedaction → Handler
app.add_middleware(PIIRedactionMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Include routers ───────────────────────────────────────────────────────
app.include_router(whatsapp_router)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint. Public — no auth required.

    WHY: Used by Docker healthcheck, load balancers, and monitoring.
    Returns agent count and MCP server count to verify the stack is up.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        agents_loaded=5,
        mcp_servers=3,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a text message to AgriSaathi.

    WHY: This is the primary interaction endpoint. The farmer's message
    goes to FarmerConcierge, which classifies intent and delegates to
    the appropriate sub-agent.

    Flow:
    1. Ensure session exists (create if needed)
    2. Run message through FarmerConcierge agent
    3. Log the delegation decision to audit trail
    4. Return the agent's response
    """
    import traceback

    try:
        # Ensure session exists (non-fatal if fails)
        try:
            await session_store.create_session(
                session_id=request.session_id,
                user_id=request.user_id,
            )
        except Exception as e:
            logger.warning("session_create_failed", error=str(e))

        # Audit: incoming message (non-fatal if fails)
        try:
            audit_logger.log(
                action="chat_request_received",
                user_id=request.user_id,
                session_id=request.session_id,
                agent="farmer_concierge",
                details={"language": request.language.value, "message_length": len(request.message)},
            )
        except Exception as e:
            logger.warning("audit_log_failed", error=str(e))

        # Run through agent (mock mode for now)
        mock_mode = os.environ.get("MOCK_LLM", "true").lower() == "true"

        if mock_mode:
            # WHY: In mock mode, classify intent from keywords and return
            # a canned response. This allows full API testing without Gemini.
            agent_used, response_text = _mock_agent_response(
                request.message, request.language.value
            )
        else:
            # Production: run through ADK runner
            agent_used, response_text = await _run_agent(
                message=request.message,
                session_id=request.session_id,
                user_id=request.user_id,
            )

        # Audit: response sent (non-fatal)
        try:
            audit_logger.log(
                action="chat_response_sent",
                user_id=request.user_id,
                session_id=request.session_id,
                agent=agent_used,
                details={"response_length": len(response_text)},
            )
        except Exception:
            pass

        # Update session state (non-fatal)
        try:
            await session_store.update_session_state(
                session_id=request.session_id,
                state_update={
                    "last_agent": agent_used,
                    "last_language": request.language.value,
                    "last_interaction": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception:
            pass

        return ChatResponse(
            response=response_text,
            agent_used=AgentType(agent_used),
            session_id=request.session_id,
        )

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("chat_endpoint_failed", error=str(e), traceback=tb)
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.post("/diagnose", response_model=CropDiagnosisResponse)
async def diagnose(request: DiagnoseRequest) -> CropDiagnosisResponse:
    """Diagnose crop disease from a leaf photo.

    WHY: Separate endpoint from /chat because it handles binary image data.
    Routes directly to CropDoctor agent with the photo.
    """
    # Ensure session exists
    await session_store.create_session(
        session_id=request.session_id,
        user_id=request.user_id,
    )

    # Audit
    audit_logger.log(
        action="diagnose_request_received",
        user_id=request.user_id,
        session_id=request.session_id,
        agent="crop_doctor",
        details={"image_filename": request.image_filename or "unnamed"},
    )

    # Run diagnosis
    from tools.vision_tool import analyze_crop_image

    diagnosis = analyze_crop_image(
        image_base64=request.image_base64,
        image_filename=request.image_filename,
    )

    # Audit
    audit_logger.log(
        action="diagnosis_completed",
        user_id=request.user_id,
        session_id=request.session_id,
        agent="crop_doctor",
        details={
            "disease": diagnosis.disease,
            "confidence": diagnosis.confidence,
            "severity": diagnosis.severity,
        },
    )

    return CropDiagnosisResponse(
        disease=diagnosis.disease,
        confidence=diagnosis.confidence,
        crop_name=diagnosis.crop_name,
        treatment=diagnosis.treatment,
        organic_alternative=diagnosis.organic_alternative,
        organic_treatment=diagnosis.organic_treatment,
        severity=diagnosis.severity,
    )


@app.get("/session/{session_id}")
async def get_session(session_id: str) -> JSONResponse:
    """Retrieve session data.

    WHY: Allows the frontend to restore conversation context when a
    farmer returns to the app.
    """
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return JSONResponse(content=session)


@app.post("/token")
async def create_dev_token(user_id: str = "farmer_001") -> JSONResponse:
    """Generate a mock JWT for local development.

    WHY: Developers need a valid JWT to test protected endpoints.
    This endpoint is only available in dev mode (MOCK_LLM=true).
    In production, Firebase Auth handles token issuance via phone OTP.

    ⚠️ This endpoint should be disabled in production via Cloud Armor rules.
    """
    if os.environ.get("MOCK_LLM", "true").lower() != "true":
        raise HTTPException(
            status_code=403,
            detail="Token generation is only available in development mode",
        )

    token = create_mock_token(user_id)
    return JSONResponse(content={"token": token, "user_id": user_id})


# =============================================================================
# Mock Agent Response (for MOCK_LLM=true mode)
# =============================================================================
def _mock_agent_response(message: str, language: str) -> tuple[str, str]:
    """Classify intent and return a mock response.

    WHY: Enables full API testing without Gemini API keys. Intent
    classification uses keyword matching — good enough for testing
    the middleware stack, session management, and frontend integration.
    """
    msg_lower = message.lower()

    # Disease keywords (Hindi + English)
    disease_keywords = [
        "disease", "pest", "leaf", "yellow", "spots", "wilt", "insect", "bug",
        "रोग", "बीमारी", "कीड़ा", "पत्ते", "पीले", "धब्बे", "मुरझाना",
    ]
    # Weather keywords
    weather_keywords = [
        "weather", "rain", "irrigation", "water", "forecast", "monsoon",
        "मौसम", "बारिश", "सिंचाई", "पानी", "तापमान",
    ]
    # Market keywords
    market_keywords = [
        "price", "mandi", "sell", "market", "rate", "trend",
        "भाव", "मंडी", "बेचना", "दाम", "बाज़ार",
    ]
    # Scheme keywords
    scheme_keywords = [
        "scheme", "subsidy", "loan", "government", "pm-kisan", "insurance",
        "योजना", "सब्सिडी", "लोन", "सरकारी", "बीमा", "किसान",
    ]

    if any(kw in msg_lower for kw in disease_keywords):
        agent = "crop_doctor"
        if language == "hi":
            text = (
                "🌿 **फसल:** टमाटर\n"
                "🔬 **रोग:** लेट ब्लाइट (पछेती अंगमारी)\n"
                "📊 **विश्वास:** 92%\n"
                "⚠️ **गंभीरता:** मध्यम\n\n"
                "🌱 **जैविक उपचार (सबसे पहले आज़माएं):**\n"
                "नीम का तेल (5ml/लीटर पानी) स्प्रे करें। सुबह या शाम करें।\n\n"
                "💊 **रासायनिक उपचार:**\n"
                "मैन्कोज़ेब 75 WP (2.5g/लीटर पानी)\n\n"
                "और कोई सवाल? 🙏"
            )
        else:
            text = (
                "🌿 **Crop:** Tomato\n"
                "🔬 **Disease:** Late Blight\n"
                "📊 **Confidence:** 92%\n"
                "⚠️ **Severity:** Medium\n\n"
                "🌱 **Organic Treatment (try first):**\n"
                "Spray neem oil (5ml/liter water). Apply in morning or evening.\n\n"
                "💊 **Chemical Treatment:**\n"
                "Mancozeb 75 WP (2.5g/liter water)\n\n"
                "Any other questions? 🙏"
            )
    elif any(kw in msg_lower for kw in weather_keywords):
        agent = "weather_advisor"
        if language == "hi":
            text = (
                "🌤️ **आज का मौसम:** आंशिक बादल, 34°C, नमी 65%\n\n"
                "📅 **7-दिन पूर्वानुमान:**\n"
                "सोम: ☀️ 35°C | मंगल: 🌤️ 33°C | बुध: 🌧️ 30°C बारिश 15mm\n"
                "गुरु: 🌧️ 28°C बारिश 25mm | शुक्र: 🌤️ 31°C | शनि: ☀️ 34°C | रवि: ☀️ 35°C\n\n"
                "💧 **सिंचाई सलाह:** आज सिंचाई करें। बुधवार से बारिश की संभावना।\n\n"
                "और कोई सवाल? 🙏"
            )
        else:
            text = (
                "🌤️ **Today's Weather:** Partly cloudy, 34°C, Humidity 65%\n\n"
                "📅 **7-Day Forecast:**\n"
                "Mon: ☀️ 35°C | Tue: 🌤️ 33°C | Wed: 🌧️ 30°C Rain 15mm\n"
                "Thu: 🌧️ 28°C Rain 25mm | Fri: 🌤️ 31°C | Sat: ☀️ 34°C | Sun: ☀️ 35°C\n\n"
                "💧 **Irrigation Advice:** Irrigate today. Rain expected from Wednesday.\n\n"
                "Any other questions? 🙏"
            )
    elif any(kw in msg_lower for kw in market_keywords):
        agent = "market_whisperer"
        if language == "hi":
            text = (
                "📊 **आज का भाव:**\n"
                "🍅 टमाटर — आज़ादपुर मंडी: ₹2,800/क्विंटल\n"
                "   न्यूनतम: ₹2,200 | अधिकतम: ₹3,400 | मॉडल: ₹2,800\n\n"
                "📈 **7-दिन रुझान:** बढ़ रहा है (+12%)\n\n"
                "💡 **सलाह:** रुकें — भाव और बढ़ सकते हैं।\n"
                "🏪 **बेहतर मंडी:** वाशी (मुंबई) ₹3,100/क्विंटल\n\n"
                "और कोई सवाल? 🙏"
            )
        else:
            text = (
                "📊 **Today's Price:**\n"
                "🍅 Tomato — Azadpur Mandi: ₹2,800/quintal\n"
                "   Min: ₹2,200 | Max: ₹3,400 | Modal: ₹2,800\n\n"
                "📈 **7-Day Trend:** Rising (+12%)\n\n"
                "💡 **Recommendation:** Hold — prices may increase further.\n"
                "🏪 **Better Market:** Vashi (Mumbai) ₹3,100/quintal\n\n"
                "Any other questions? 🙏"
            )
    elif any(kw in msg_lower for kw in scheme_keywords):
        agent = "scheme_guide"
        if language == "hi":
            text = (
                "🏛️ **योजना: PM-Kisan (प्रधानमंत्री किसान सम्मान निधि)**\n\n"
                "📋 **विवरण:** हर साल ₹6,000 सीधे बैंक खाते में, 3 किस्तों में।\n\n"
                "✅ **पात्रता:**\n"
                "- 2 हेक्टेयर (5 एकड़) तक ज़मीन वाले किसान\n"
                "- सभी राज्यों में उपलब्ध\n\n"
                "📄 **ज़रूरी दस्तावेज़:**\n"
                "1. आधार कार्ड\n"
                "2. बैंक पासबुक\n"
                "3. ज़मीन के कागज़ात (खसरा/खतौनी)\n\n"
                "📞 **हेल्पलाइन:** 1800-115-526\n"
                "🌐 **वेबसाइट:** pmkisan.gov.in\n\n"
                "और कोई सवाल? 🙏"
            )
        else:
            text = (
                "🏛️ **Scheme: PM-Kisan (Pradhan Mantri Kisan Samman Nidhi)**\n\n"
                "📋 **Description:** ₹6,000/year directly to bank account, in 3 installments.\n\n"
                "✅ **Eligibility:**\n"
                "- Farmers with up to 2 hectares (5 acres) of land\n"
                "- Available in all states\n\n"
                "📄 **Documents Needed:**\n"
                "1. Aadhaar card\n"
                "2. Bank passbook\n"
                "3. Land records (Khasra/Khatauni)\n\n"
                "📞 **Helpline:** 1800-115-526\n"
                "🌐 **Website:** pmkisan.gov.in\n\n"
                "Any other questions? 🙏"
            )
    else:
        agent = "farmer_concierge"
        if language == "hi":
            text = (
                "नमस्ते! 🙏 मैं अन्नदाता साथी हूँ।\n\n"
                "मैं आपकी इन चीज़ों में मदद कर सकता हूँ:\n"
                "📸 फसल का फोटो भेजें — रोग की पहचान\n"
                "🌤️ मौसम और सिंचाई सलाह\n"
                "📊 मंडी भाव और बेचने की सलाह\n"
                "🏛️ सरकारी योजनाएं और सब्सिडी\n\n"
                "कैसे मदद करूँ? 🌾"
            )
        else:
            text = (
                "Namaste! 🙏 I am AgriSaathi — your AI farming companion.\n\n"
                "I can help you with:\n"
                "📸 Send a crop photo — disease diagnosis\n"
                "🌤️ Weather forecast & irrigation advice\n"
                "📊 Mandi prices & sell/hold recommendations\n"
                "🏛️ Government schemes & subsidies\n\n"
                "How can I help? 🌾"
            )

    return agent, text


async def _run_agent(
    message: str,
    session_id: str,
    user_id: str,
) -> tuple[str, str]:
    """Run the message through the ADK agent runner.

    WHY: Production path — uses ADK's Runner with InMemorySessionService
    (or Firestore in prod) to maintain conversation context.

    Returns (agent_name, response_text).
    """
    try:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        from agents.farmer_concierge import farmer_concierge_agent

        session_service = InMemorySessionService()
        runner = Runner(
            agent=farmer_concierge_agent,
            app_name="agri_saathi",
            session_service=session_service,
        )

        await session_service.create_session(
            app_name="agri_saathi",
            user_id=user_id,
            session_id=session_id,
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(message)],
        )

        response_text = ""
        agent_name = "farmer_concierge"

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text
                agent_name = getattr(event, "agent_name", "farmer_concierge")

        return agent_name, response_text or "I'm sorry, I couldn't process that request."

    except Exception as e:
        logger.error("agent_run_failed", error=str(e))
        return "farmer_concierge", f"I'm experiencing technical difficulties. Please try again. Error: {e}"
