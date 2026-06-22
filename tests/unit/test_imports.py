"""
AgriSaathi — Import Smoke Test (Guardrail)
============================================
WHY: If any agent module fails to import, the entire system is broken.
This test catches import errors at CI time, not at runtime when a farmer
is waiting for a diagnosis.

If this test fails, the build is broken — fail loudly.
"""

import pytest


def test_import_crop_doctor():
    """CropDoctor agent must be importable."""
    from agents.crop_doctor import crop_doctor_agent
    assert crop_doctor_agent.name == "crop_doctor"


def test_import_weather_advisor():
    """WeatherAdvisor agent must be importable."""
    from agents.weather_advisor import weather_advisor_agent
    assert weather_advisor_agent.name == "weather_advisor"


def test_import_market_whisperer():
    """MarketWhisperer agent must be importable."""
    from agents.market_whisperer import market_whisperer_agent
    assert market_whisperer_agent.name == "market_whisperer"


def test_import_scheme_guide():
    """SchemeGuide agent must be importable."""
    from agents.scheme_guide import scheme_guide_agent
    assert scheme_guide_agent.name == "scheme_guide"


def test_import_farmer_concierge():
    """FarmerConcierge root agent must be importable with all sub-agents."""
    from agents.farmer_concierge import farmer_concierge_agent
    assert farmer_concierge_agent.name == "farmer_concierge"
    assert len(farmer_concierge_agent.sub_agents) == 4


def test_import_vision_tool():
    """Vision tool must be importable."""
    from tools.vision_tool import analyze_crop_image, CropDiagnosis
    assert callable(analyze_crop_image)
    assert CropDiagnosis is not None


def test_import_api_models():
    """API models must be importable."""
    from api.models import ChatRequest, ChatResponse, DiagnoseRequest
    assert ChatRequest is not None
    assert ChatResponse is not None
    assert DiagnoseRequest is not None


def test_import_security():
    """Security middleware must be importable."""
    from api.security import (
        PIIRedactionMiddleware,
        JWTAuthMiddleware,
        RateLimitMiddleware,
        AuditLogger,
    )
    assert PIIRedactionMiddleware is not None
    assert AuditLogger is not None


def test_import_session_store():
    """Session store must be importable."""
    from api.session_store import SQLiteSessionStore
    store = SQLiteSessionStore(db_path=":memory:")
    assert store is not None
