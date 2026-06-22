"""
WHY: Converts raw mandi-price API data into simple, actionable text a
low-literacy farmer can understand — over voice (TTS), SMS, or WhatsApp.

Indian farmers often sell at the wrong time because they can't interpret
tabular market data.  These formatters turn price dictionaries into plain
Hindi or English sentences with clear buy/sell/hold advice.
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

_MOCK_MODE: bool = os.environ.get("MOCK_LLM", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------

_SUPPORTED_LANGS: set[str] = {"en", "hi"}


def _validate_language(language: str) -> str:
    """Normalise and validate language code.

    WHY: Fail-fast with a clear message instead of silently falling back.
    """
    lang = language.strip().lower()
    if lang not in _SUPPORTED_LANGS:
        log.warning("unsupported_language_fallback", requested=lang, using="en")
        return "en"
    return lang


# ---------------------------------------------------------------------------
# Pydantic models for structured input (optional but encouraged)
# ---------------------------------------------------------------------------

class PriceData(BaseModel):
    """Mandi price snapshot for a single commodity.

    WHY: Validates upstream API responses before formatting — catches
    missing fields early so the farmer never sees a broken message.
    """

    commodity: str = Field(..., description="Crop name, e.g. 'Wheat'")
    mandi: str = Field(..., description="Market name, e.g. 'Azadpur'")
    state: str = Field("", description="State name, e.g. 'Delhi'")
    min_price: float = Field(..., description="Minimum price ₹/quintal")
    max_price: float = Field(..., description="Maximum price ₹/quintal")
    modal_price: float = Field(..., description="Most-traded price ₹/quintal")
    unit: str = Field("₹/quintal", description="Price unit")
    date: str = Field("", description="Price date YYYY-MM-DD")


class TrendData(BaseModel):
    """Price trend over a time window.

    WHY: Gives farmers a sense of direction so they can decide to hold or
    sell their produce.
    """

    commodity: str
    mandi: str
    current_price: float
    previous_price: float
    change_pct: float = Field(..., description="Percentage change, e.g. +5.2 or -3.1")
    period: str = Field("week", description="Comparison period: day / week / month")
    trend: str = Field("stable", description="up / down / stable")


class Recommendation(BaseModel):
    """Simple actionable recommendation.

    WHY: The final farmer-facing advice — sell now, hold, or wait.
    """

    commodity: str
    action: str = Field(..., description="sell / hold / wait")
    reason: str
    target_price: float | None = None
    target_mandi: str | None = None


# ---------------------------------------------------------------------------
# Hindi translation maps
# ---------------------------------------------------------------------------

_HI_ACTIONS: dict[str, str] = {
    "sell": "बेचें",
    "hold": "रोक कर रखें",
    "wait": "इंतज़ार करें",
}

_HI_TRENDS: dict[str, str] = {
    "up": "बढ़ रहे हैं",
    "down": "गिर रहे हैं",
    "stable": "स्थिर हैं",
}

_HI_PERIODS: dict[str, str] = {
    "day": "कल से",
    "week": "पिछले हफ़्ते से",
    "month": "पिछले महीने से",
}


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_price_for_farmer(price_data: dict[str, Any], language: str = "en") -> str:
    """Format a single mandi price snapshot into farmer-friendly text.

    WHY: Raw API JSON is useless to a farmer listening over a phone call.
    This returns a concise sentence she can act on.

    Args:
        price_data: Dict matching PriceData schema (or a PriceData.model_dump()).
        language: 'en' or 'hi'.

    Returns:
        Human-readable price string.
    """
    lang = _validate_language(language)
    pd = PriceData(**price_data)

    log.info(
        "format_price",
        commodity=pd.commodity,
        mandi=pd.mandi,
        modal_price=pd.modal_price,
        language=lang,
    )

    if lang == "hi":
        date_part = f" ({pd.date})" if pd.date else ""
        return (
            f"📊 {pd.commodity} — {pd.mandi} मंडी{', ' + pd.state if pd.state else ''}{date_part}\n"
            f"न्यूनतम: ₹{pd.min_price:,.0f} | अधिकतम: ₹{pd.max_price:,.0f} | "
            f"सामान्य: ₹{pd.modal_price:,.0f} प्रति क्विंटल"
        )

    # English
    date_part = f" ({pd.date})" if pd.date else ""
    return (
        f"📊 {pd.commodity} — {pd.mandi} Mandi{', ' + pd.state if pd.state else ''}{date_part}\n"
        f"Min: ₹{pd.min_price:,.0f} | Max: ₹{pd.max_price:,.0f} | "
        f"Modal: ₹{pd.modal_price:,.0f} per quintal"
    )


def format_trend_summary(trend_data: dict[str, Any], language: str = "en") -> str:
    """Format price trend into a simple directional sentence.

    WHY: Farmers need to know if prices are rising or falling, not a
    time-series chart.  A single sentence with an emoji arrow suffices.

    Args:
        trend_data: Dict matching TrendData schema.
        language: 'en' or 'hi'.

    Returns:
        Human-readable trend string.
    """
    lang = _validate_language(language)
    td = TrendData(**trend_data)

    # Direction emoji
    arrow = "📈" if td.trend == "up" else ("📉" if td.trend == "down" else "➡️")
    change_sign = "+" if td.change_pct >= 0 else ""

    log.info(
        "format_trend",
        commodity=td.commodity,
        trend=td.trend,
        change_pct=td.change_pct,
        language=lang,
    )

    if lang == "hi":
        period_hi = _HI_PERIODS.get(td.period, td.period)
        trend_hi = _HI_TRENDS.get(td.trend, td.trend)
        return (
            f"{arrow} {td.commodity} के भाव {period_hi} {trend_hi}\n"
            f"पहले: ₹{td.previous_price:,.0f} → अभी: ₹{td.current_price:,.0f} "
            f"({change_sign}{td.change_pct:.1f}%)"
        )

    return (
        f"{arrow} {td.commodity} prices are {td.trend} ({change_sign}{td.change_pct:.1f}%) "
        f"compared to last {td.period}\n"
        f"Previous: ₹{td.previous_price:,.0f} → Current: ₹{td.current_price:,.0f} "
        f"at {td.mandi}"
    )


def format_recommendation(rec_data: dict[str, Any], language: str = "en") -> str:
    """Format an actionable sell/hold/wait recommendation.

    WHY: The single most important output — tells the farmer what to DO
    with their harvest right now.

    Args:
        rec_data: Dict matching Recommendation schema.
        language: 'en' or 'hi'.

    Returns:
        Human-readable recommendation string.
    """
    lang = _validate_language(language)
    rec = Recommendation(**rec_data)

    action_emoji = {"sell": "✅", "hold": "⏳", "wait": "🕐"}.get(rec.action, "ℹ️")

    log.info(
        "format_recommendation",
        commodity=rec.commodity,
        action=rec.action,
        language=lang,
    )

    if lang == "hi":
        action_hi = _HI_ACTIONS.get(rec.action, rec.action)
        target_part = ""
        if rec.target_price:
            target_part = f"\nलक्ष्य मूल्य: ₹{rec.target_price:,.0f} प्रति क्विंटल"
        if rec.target_mandi:
            target_part += f"\nसबसे अच्छी मंडी: {rec.target_mandi}"
        return (
            f"{action_emoji} सलाह: {rec.commodity} अभी {action_hi}\n"
            f"कारण: {rec.reason}{target_part}"
        )

    # English
    target_part = ""
    if rec.target_price:
        target_part = f"\nTarget price: ₹{rec.target_price:,.0f}/quintal"
    if rec.target_mandi:
        target_part += f"\nBest mandi: {rec.target_mandi}"
    return (
        f"{action_emoji} Advice: {rec.action.upper()} {rec.commodity}\n"
        f"Reason: {rec.reason}{target_part}"
    )
