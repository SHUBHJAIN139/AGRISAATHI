"""
WHY: Translates raw weather forecast data into concrete farming decisions —
when to irrigate, when NOT to spray, when to harvest early.  Most Indian
smallholder farmers cannot interpret meteorological data; they need
plain-language advice tied to their current crop stage.

Supports English and Hindi output for voice (TTS) and text delivery.
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

_MOCK_MODE: bool = os.environ.get("MOCK_LLM", "true").lower() == "true"

_SUPPORTED_LANGS: set[str] = {"en", "hi"}


def _validate_language(language: str) -> str:
    """Normalise and validate language code."""
    lang = language.strip().lower()
    if lang not in _SUPPORTED_LANGS:
        log.warning("unsupported_language_fallback", requested=lang, using="en")
        return "en"
    return lang


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ForecastDay(BaseModel):
    """Single-day weather forecast.

    WHY: Validates upstream weather API responses — ensures we never format
    a message with missing temperature or rainfall data.
    """

    date: str = Field(..., description="Date string YYYY-MM-DD")
    temp_min_c: float = Field(..., description="Minimum temperature °C")
    temp_max_c: float = Field(..., description="Maximum temperature °C")
    humidity_pct: float = Field(..., description="Average relative humidity %")
    rainfall_mm: float = Field(0.0, description="Expected rainfall in mm")
    wind_speed_kmh: float = Field(0.0, description="Wind speed km/h")
    condition: str = Field("Clear", description="Summary: Clear / Cloudy / Rain / Storm")
    uv_index: float = Field(0.0, description="UV index 0-11+")


class Forecast(BaseModel):
    """Multi-day forecast wrapper.

    WHY: Groups daily forecasts with location metadata so formatters
    can include the district/block name the farmer recognises.
    """

    location: str = Field(..., description="Village / district name")
    state: str = Field("", description="State name")
    days: list[ForecastDay] = Field(..., min_length=1)


class IrrigationAdvice(BaseModel):
    """Irrigation scheduling recommendation.

    WHY: Over-irrigation wastes scarce groundwater; under-irrigation kills
    yield.  This struct gives a clear schedule tied to forecast rainfall.
    """

    crop: str
    current_stage: str = Field("vegetative", description="Growth stage of the crop")
    soil_type: str = Field("loam", description="Soil type: sandy / loam / clay / black cotton")
    irrigate_today: bool
    next_irrigation_date: str = Field("", description="Suggested next date")
    reason: str
    water_mm: float = Field(0.0, description="Recommended depth in mm")


class CropWeatherRisk(BaseModel):
    """Risk assessment tying weather to crop vulnerability.

    WHY: A farmer growing tomatoes needs different warnings than one
    growing wheat.  This model pairs forecast conditions with crop-specific
    vulnerabilities.
    """

    risk_level: str = Field(..., description="low / medium / high / critical")
    risks: list[str] = Field(default_factory=list, description="List of identified risks")
    precautions: list[str] = Field(default_factory=list, description="Actionable precautions")


# ---------------------------------------------------------------------------
# Hindi translation helpers
# ---------------------------------------------------------------------------

_HI_CONDITIONS: dict[str, str] = {
    "Clear": "साफ़ मौसम",
    "Cloudy": "बादल छाए",
    "Rain": "बारिश",
    "Storm": "आँधी-तूफ़ान",
    "Haze": "धुंध",
    "Fog": "कोहरा",
    "Drizzle": "बूँदाबाँदी",
    "Thunderstorm": "गरज के साथ बारिश",
}

_HI_RISK_LEVELS: dict[str, str] = {
    "low": "कम",
    "medium": "मध्यम",
    "high": "ज़्यादा",
    "critical": "गंभीर",
}


# ---------------------------------------------------------------------------
# Crop-specific weather thresholds
# ---------------------------------------------------------------------------
# WHY: Different crops have different vulnerabilities. These thresholds let
# us give crop-specific warnings without an LLM call in mock mode.

_CROP_THRESHOLDS: dict[str, dict[str, Any]] = {
    "tomato": {
        "heat_max_c": 38.0,
        "cold_min_c": 10.0,
        "rain_disease_mm": 20.0,
        "humidity_disease_pct": 85.0,
        "wind_damage_kmh": 40.0,
        "frost_risk_c": 2.0,
        "diseases_from_rain": ["Late Blight", "Early Blight", "Bacterial Spot"],
        "diseases_from_humidity": ["Leaf Mold", "Septoria Leaf Spot"],
    },
    "potato": {
        "heat_max_c": 35.0,
        "cold_min_c": 5.0,
        "rain_disease_mm": 25.0,
        "humidity_disease_pct": 80.0,
        "wind_damage_kmh": 45.0,
        "frost_risk_c": 0.0,
        "diseases_from_rain": ["Late Blight"],
        "diseases_from_humidity": ["Early Blight"],
    },
    "wheat": {
        "heat_max_c": 35.0,
        "cold_min_c": 0.0,
        "rain_disease_mm": 30.0,
        "humidity_disease_pct": 80.0,
        "wind_damage_kmh": 50.0,
        "frost_risk_c": -2.0,
        "diseases_from_rain": ["Rust", "Karnal Bunt"],
        "diseases_from_humidity": ["Powdery Mildew"],
    },
    "rice": {
        "heat_max_c": 40.0,
        "cold_min_c": 15.0,
        "rain_disease_mm": 50.0,
        "humidity_disease_pct": 90.0,
        "wind_damage_kmh": 45.0,
        "frost_risk_c": 10.0,
        "diseases_from_rain": ["Bacterial Leaf Blight"],
        "diseases_from_humidity": ["Blast", "Sheath Blight"],
    },
    "corn": {
        "heat_max_c": 38.0,
        "cold_min_c": 8.0,
        "rain_disease_mm": 25.0,
        "humidity_disease_pct": 85.0,
        "wind_damage_kmh": 40.0,
        "frost_risk_c": 2.0,
        "diseases_from_rain": ["Northern Leaf Blight"],
        "diseases_from_humidity": ["Common Rust", "Gray Leaf Spot"],
    },
    "apple": {
        "heat_max_c": 35.0,
        "cold_min_c": -5.0,
        "rain_disease_mm": 15.0,
        "humidity_disease_pct": 80.0,
        "wind_damage_kmh": 50.0,
        "frost_risk_c": -3.0,
        "diseases_from_rain": ["Apple Scab", "Black Rot"],
        "diseases_from_humidity": ["Powdery Mildew"],
    },
    "grape": {
        "heat_max_c": 40.0,
        "cold_min_c": 5.0,
        "rain_disease_mm": 10.0,
        "humidity_disease_pct": 75.0,
        "wind_damage_kmh": 35.0,
        "frost_risk_c": 0.0,
        "diseases_from_rain": ["Downy Mildew", "Black Rot"],
        "diseases_from_humidity": ["Powdery Mildew"],
    },
}

# Fallback for unknown crops
_DEFAULT_THRESHOLDS: dict[str, Any] = {
    "heat_max_c": 40.0,
    "cold_min_c": 5.0,
    "rain_disease_mm": 30.0,
    "humidity_disease_pct": 85.0,
    "wind_damage_kmh": 50.0,
    "frost_risk_c": 0.0,
    "diseases_from_rain": ["Fungal diseases"],
    "diseases_from_humidity": ["Fungal diseases"],
}


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_forecast_for_farmer(
    forecast: dict[str, Any], language: str = "en"
) -> str:
    """Format multi-day weather forecast into farmer-friendly text.

    WHY: Farmers need to know three things — will it rain, how hot/cold,
    and should I spray today.  This collapses a JSON blob into those
    answers.

    Args:
        forecast: Dict matching Forecast schema.
        language: 'en' or 'hi'.

    Returns:
        Multi-line human-readable forecast.
    """
    lang = _validate_language(language)
    fc = Forecast(**forecast)

    log.info(
        "format_forecast",
        location=fc.location,
        num_days=len(fc.days),
        language=lang,
    )

    lines: list[str] = []

    if lang == "hi":
        header = f"🌤️ मौसम — {fc.location}"
        if fc.state:
            header += f", {fc.state}"
        lines.append(header)
        lines.append("─" * 30)

        for day in fc.days:
            condition_hi = _HI_CONDITIONS.get(day.condition, day.condition)
            rain_part = f" | 🌧️ {day.rainfall_mm:.0f} mm बारिश" if day.rainfall_mm > 0 else ""
            wind_part = f" | 💨 {day.wind_speed_kmh:.0f} km/h" if day.wind_speed_kmh > 20 else ""
            lines.append(
                f"📅 {day.date}: {condition_hi}, "
                f"🌡️ {day.temp_min_c:.0f}–{day.temp_max_c:.0f}°C"
                f"{rain_part}{wind_part}"
            )

        # Summary advice
        total_rain = sum(d.rainfall_mm for d in fc.days)
        if total_rain > 50:
            lines.append("\n⚠️ भारी बारिश की संभावना — छिड़काव न करें, जल निकासी सुनिश्चित करें")
        elif total_rain > 0:
            lines.append("\n💧 हल्की बारिश — सिंचाई की ज़रूरत नहीं")
        else:
            lines.append("\n☀️ सूखा मौसम — सिंचाई का समय निकालें")
    else:
        header = f"🌤️ Weather — {fc.location}"
        if fc.state:
            header += f", {fc.state}"
        lines.append(header)
        lines.append("─" * 30)

        for day in fc.days:
            rain_part = f" | 🌧️ {day.rainfall_mm:.0f} mm" if day.rainfall_mm > 0 else ""
            wind_part = f" | 💨 {day.wind_speed_kmh:.0f} km/h" if day.wind_speed_kmh > 20 else ""
            lines.append(
                f"📅 {day.date}: {day.condition}, "
                f"🌡️ {day.temp_min_c:.0f}–{day.temp_max_c:.0f}°C"
                f"{rain_part}{wind_part}"
            )

        total_rain = sum(d.rainfall_mm for d in fc.days)
        if total_rain > 50:
            lines.append("\n⚠️ Heavy rain expected — avoid spraying, ensure drainage")
        elif total_rain > 0:
            lines.append("\n💧 Light rain expected — skip irrigation")
        else:
            lines.append("\n☀️ Dry spell — plan irrigation")

    return "\n".join(lines)


def format_irrigation_advice(
    irrigation: dict[str, Any], language: str = "en"
) -> str:
    """Format irrigation recommendation into farmer-friendly text.

    WHY: Over-pumping groundwater is the #1 resource waste in Indian
    agriculture.  Clear yes/no irrigation advice saves water and money.

    Args:
        irrigation: Dict matching IrrigationAdvice schema.
        language: 'en' or 'hi'.

    Returns:
        Concise irrigation instruction.
    """
    lang = _validate_language(language)
    irr = IrrigationAdvice(**irrigation)

    log.info(
        "format_irrigation",
        crop=irr.crop,
        irrigate_today=irr.irrigate_today,
        water_mm=irr.water_mm,
        language=lang,
    )

    if lang == "hi":
        action = "✅ आज सिंचाई करें" if irr.irrigate_today else "❌ आज सिंचाई न करें"
        water_part = f"\n💧 पानी: {irr.water_mm:.0f} mm" if irr.water_mm > 0 else ""
        next_part = (
            f"\n📅 अगली सिंचाई: {irr.next_irrigation_date}"
            if irr.next_irrigation_date
            else ""
        )
        return (
            f"🌾 {irr.crop} ({irr.current_stage} अवस्था) — {irr.soil_type} मिट्टी\n"
            f"{action}\n"
            f"कारण: {irr.reason}{water_part}{next_part}"
        )

    # English
    action = "✅ Irrigate today" if irr.irrigate_today else "❌ Do NOT irrigate today"
    water_part = f"\n💧 Water needed: {irr.water_mm:.0f} mm" if irr.water_mm > 0 else ""
    next_part = (
        f"\n📅 Next irrigation: {irr.next_irrigation_date}"
        if irr.next_irrigation_date
        else ""
    )
    return (
        f"🌾 {irr.crop} ({irr.current_stage} stage) — {irr.soil_type} soil\n"
        f"{action}\n"
        f"Reason: {irr.reason}{water_part}{next_part}"
    )


# ---------------------------------------------------------------------------
# Crop-Weather Risk Assessment
# ---------------------------------------------------------------------------

def get_crop_weather_risk(
    crop: str, forecast: dict[str, Any]
) -> dict[str, Any]:
    """Assess weather risk for a specific crop given a forecast.

    WHY: A tomato farmer needs fungicide warnings when humidity spikes; a
    wheat farmer needs frost alerts.  Generic weather data is not enough —
    this function cross-references crop-specific thresholds with the actual
    forecast to produce targeted risk assessments.

    Args:
        crop: Crop name (case-insensitive).
        forecast: Dict matching Forecast schema.

    Returns:
        Dict matching CropWeatherRisk schema:
        ``{risk_level, risks: [str], precautions: [str]}``
    """
    fc = Forecast(**forecast)
    crop_lower = crop.strip().lower()
    thresholds = _CROP_THRESHOLDS.get(crop_lower, _DEFAULT_THRESHOLDS)

    risks: list[str] = []
    precautions: list[str] = []

    for day in fc.days:
        # ── Heat stress ──────────────────────────────────────────────
        if day.temp_max_c >= thresholds["heat_max_c"]:
            risk_msg = (
                f"Heat stress on {day.date}: {day.temp_max_c:.0f}°C "
                f"exceeds {crop} tolerance ({thresholds['heat_max_c']:.0f}°C)"
            )
            if risk_msg not in risks:
                risks.append(risk_msg)
                precautions.append(
                    f"Provide shade / mulch; irrigate in early morning on {day.date}"
                )

        # ── Cold / frost ─────────────────────────────────────────────
        if day.temp_min_c <= thresholds["frost_risk_c"]:
            risk_msg = (
                f"Frost risk on {day.date}: {day.temp_min_c:.0f}°C "
                f"near frost threshold ({thresholds['frost_risk_c']:.0f}°C)"
            )
            if risk_msg not in risks:
                risks.append(risk_msg)
                precautions.append(
                    f"Cover crop with straw / plastic sheets on evening of {day.date}"
                )

        # ── Rain → disease ───────────────────────────────────────────
        if day.rainfall_mm >= thresholds["rain_disease_mm"]:
            disease_names = ", ".join(thresholds["diseases_from_rain"])
            risk_msg = (
                f"Heavy rain on {day.date}: {day.rainfall_mm:.0f} mm — "
                f"risk of {disease_names}"
            )
            if risk_msg not in risks:
                risks.append(risk_msg)
                precautions.append(
                    f"Apply preventive fungicide BEFORE rain on {day.date}; "
                    f"ensure field drainage"
                )

        # ── High humidity → disease ──────────────────────────────────
        if day.humidity_pct >= thresholds["humidity_disease_pct"]:
            disease_names = ", ".join(thresholds["diseases_from_humidity"])
            risk_msg = (
                f"High humidity on {day.date}: {day.humidity_pct:.0f}% — "
                f"risk of {disease_names}"
            )
            if risk_msg not in risks:
                risks.append(risk_msg)
                precautions.append(
                    f"Improve canopy airflow; avoid overhead irrigation on {day.date}"
                )

        # ── Strong wind ──────────────────────────────────────────────
        if day.wind_speed_kmh >= thresholds["wind_damage_kmh"]:
            risk_msg = (
                f"Strong wind on {day.date}: {day.wind_speed_kmh:.0f} km/h — "
                f"physical damage risk"
            )
            if risk_msg not in risks:
                risks.append(risk_msg)
                precautions.append(
                    f"Stake / support plants; do NOT spray on {day.date} (drift risk)"
                )

    # ── Determine overall risk level ─────────────────────────────────
    if len(risks) == 0:
        risk_level = "low"
    elif len(risks) <= 2:
        risk_level = "medium"
    elif len(risks) <= 4:
        risk_level = "high"
    else:
        risk_level = "critical"

    result = CropWeatherRisk(
        risk_level=risk_level,
        risks=risks,
        precautions=precautions,
    )

    log.info(
        "crop_weather_risk",
        crop=crop,
        location=fc.location,
        risk_level=result.risk_level,
        num_risks=len(result.risks),
    )

    return result.model_dump()
