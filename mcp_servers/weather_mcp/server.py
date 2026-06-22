"""
Weather & Irrigation MCP Server for AgriSaathi.

WHY: Indian farmers need hyperlocal weather intelligence to time sowing, irrigation,
and harvesting. This server provides weather forecasts, soil moisture readings, and
deterministic irrigation advice — the three pillars of precision agriculture in
smallholder contexts. Combining all three in one server avoids cross-server round-trips
for the most latency-sensitive agricultural decision: "Should I irrigate today?"
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging — stderr only so we never corrupt the stdio JSON-RPC transport
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("weather_mcp")

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "AgriSaathi Weather MCP",
    description=(
        "Provides 7-day weather forecasts for major Indian cities, "
        "soil moisture data, and deterministic irrigation advice."
    ),
)

# ---------------------------------------------------------------------------
# Constants — supported cities & their baseline climate profiles
# ---------------------------------------------------------------------------

# WHY: Each city has a distinct agro-climatic zone. Baseline temps and rainfall
# patterns let us generate realistic mock data without an external API.
CITY_PROFILES: dict[str, dict[str, Any]] = {
    "Delhi": {
        "base_temp_min": 25, "base_temp_max": 42, "humidity": 55,
        "monsoon_rainfall": 60, "dry_rainfall": 2, "zone": "Indo-Gangetic Plains",
    },
    "Mumbai": {
        "base_temp_min": 26, "base_temp_max": 35, "humidity": 78,
        "monsoon_rainfall": 85, "dry_rainfall": 5, "zone": "Western Coast",
    },
    "Chennai": {
        "base_temp_min": 27, "base_temp_max": 38, "humidity": 72,
        "monsoon_rainfall": 45, "dry_rainfall": 3, "zone": "Eastern Coast",
    },
    "Kolkata": {
        "base_temp_min": 26, "base_temp_max": 36, "humidity": 75,
        "monsoon_rainfall": 70, "dry_rainfall": 4, "zone": "Eastern Plains",
    },
    "Bengaluru": {
        "base_temp_min": 20, "base_temp_max": 33, "humidity": 65,
        "monsoon_rainfall": 50, "dry_rainfall": 3, "zone": "Deccan Plateau",
    },
    "Hyderabad": {
        "base_temp_min": 23, "base_temp_max": 39, "humidity": 58,
        "monsoon_rainfall": 55, "dry_rainfall": 2, "zone": "Deccan Plateau",
    },
    "Jaipur": {
        "base_temp_min": 25, "base_temp_max": 43, "humidity": 40,
        "monsoon_rainfall": 45, "dry_rainfall": 1, "zone": "Arid Western",
    },
    "Lucknow": {
        "base_temp_min": 26, "base_temp_max": 41, "humidity": 60,
        "monsoon_rainfall": 55, "dry_rainfall": 2, "zone": "Indo-Gangetic Plains",
    },
    "Patna": {
        "base_temp_min": 26, "base_temp_max": 38, "humidity": 68,
        "monsoon_rainfall": 65, "dry_rainfall": 3, "zone": "Indo-Gangetic Plains",
    },
    "Bhopal": {
        "base_temp_min": 24, "base_temp_max": 40, "humidity": 52,
        "monsoon_rainfall": 50, "dry_rainfall": 2, "zone": "Central Plateau",
    },
    "Pune": {
        "base_temp_min": 22, "base_temp_max": 36, "humidity": 60,
        "monsoon_rainfall": 55, "dry_rainfall": 3, "zone": "Western Ghats",
    },
    "Nagpur": {
        "base_temp_min": 24, "base_temp_max": 43, "humidity": 48,
        "monsoon_rainfall": 55, "dry_rainfall": 2, "zone": "Vidarbha",
    },
}

CONDITIONS = ["sunny", "cloudy", "rainy", "thunderstorm"]

# WHY: Soil types mapped by lat/lon bands approximate India's major soil regions
# without needing a full GIS database.
SOIL_TYPES: list[dict[str, Any]] = [
    {"name": "Alluvial", "ph_range": (6.5, 7.5), "oc_range": (0.4, 0.8)},
    {"name": "Black Cotton (Regur)", "ph_range": (7.0, 8.5), "oc_range": (0.5, 1.0)},
    {"name": "Red Laterite", "ph_range": (5.5, 6.5), "oc_range": (0.3, 0.6)},
    {"name": "Sandy Loam", "ph_range": (6.0, 7.0), "oc_range": (0.2, 0.5)},
]

# WHY: Crop-specific irrigation methods reflect real agronomic practice in India.
CROP_IRRIGATION_METHODS: dict[str, str] = {
    "rice": "flood",
    "wheat": "sprinkler",
    "tomato": "drip",
    "onion": "drip",
    "potato": "sprinkler",
    "cotton": "drip",
    "soybean": "sprinkler",
    "mustard": "sprinkler",
    "sugarcane": "flood",
    "turmeric": "drip",
}

# Default for crops not in the lookup
DEFAULT_IRRIGATION_METHOD = "sprinkler"


# ---------------------------------------------------------------------------
# Pydantic models — enforce structure on every response
# ---------------------------------------------------------------------------

class DayForecast(BaseModel):
    """Single-day weather forecast."""
    date: str
    temp_min_c: float
    temp_max_c: float
    humidity_percent: float
    rainfall_mm: float
    wind_speed_kmh: float
    condition: str


class ForecastResponse(BaseModel):
    """Full multi-day forecast for a city."""
    city: str
    agro_climatic_zone: str
    generated_at: str
    days: list[DayForecast]


class SoilMoistureResponse(BaseModel):
    """Soil moisture and nutrient profile for a geo-point."""
    latitude: float
    longitude: float
    moisture_percent: float
    soil_type: str
    ph_level: float
    nitrogen_kg_ha: float
    phosphorus_kg_ha: float
    potassium_kg_ha: float
    organic_carbon_percent: float


class IrrigationAdvice(BaseModel):
    """Deterministic irrigation recommendation."""
    crop: str
    should_irrigate: bool
    reason: str
    recommended_mm: float
    method: str


# ---------------------------------------------------------------------------
# Helpers — deterministic pseudo-random from seed strings
# ---------------------------------------------------------------------------

def _seeded_float(seed: str, low: float, high: float) -> float:
    """
    WHY: We need *stable* mock data — the same inputs must always produce the same
    output so that agent tests are reproducible. Using a hash-based PRNG avoids
    external randomness while giving realistic-looking variance.
    """
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    fraction = (h % 10000) / 10000.0
    return round(low + fraction * (high - low), 2)


def _is_monsoon(d: date) -> bool:
    """WHY: June–September is the Indian monsoon; weather patterns shift dramatically."""
    return d.month in (6, 7, 8, 9)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_forecast(city: str, days: int = 7) -> dict[str, Any]:
    """
    Return a realistic 7-day weather forecast for an Indian city.

    WHY: Sowing, spraying, and harvesting windows are weather-dependent. Farmers
    lose ₹thousands if they spray before unexpected rain or irrigate right before
    monsoon showers. This tool gives the agent weather context for every advisory.

    Args:
        city: One of the 12 supported Indian cities.
        days: Number of forecast days (1–7, default 7).
    """
    log.info("get_forecast called: city=%s, days=%d", city, days)

    city_title = city.strip().title()
    if city_title not in CITY_PROFILES:
        supported = ", ".join(sorted(CITY_PROFILES))
        return {"error": f"Unsupported city '{city}'. Supported: {supported}"}

    days = max(1, min(days, 7))
    profile = CITY_PROFILES[city_title]
    today = date.today()

    forecasts: list[DayForecast] = []
    for i in range(days):
        d = today + timedelta(days=i)
        seed_base = f"{city_title}-{d.isoformat()}"
        monsoon = _is_monsoon(d)

        # Temperature — cooler in monsoon, hotter in May/June pre-monsoon
        temp_adj = -3.0 if monsoon else 0.0
        temp_min = _seeded_float(f"{seed_base}-tmin", profile["base_temp_min"] + temp_adj - 2, profile["base_temp_min"] + temp_adj + 2)
        temp_max = _seeded_float(f"{seed_base}-tmax", profile["base_temp_max"] + temp_adj - 3, profile["base_temp_max"] + temp_adj + 1)

        # Humidity — higher in monsoon
        hum_base = profile["humidity"] + (15 if monsoon else 0)
        humidity = _seeded_float(f"{seed_base}-hum", max(30, hum_base - 10), min(98, hum_base + 10))

        # Rainfall — dramatically higher in monsoon
        rain_base = profile["monsoon_rainfall"] if monsoon else profile["dry_rainfall"]
        rainfall = _seeded_float(f"{seed_base}-rain", 0, rain_base * 1.5)

        # Wind
        wind = _seeded_float(f"{seed_base}-wind", 5, 35)

        # Condition derived from rainfall
        if rainfall > 40:
            condition = "thunderstorm"
        elif rainfall > 10:
            condition = "rainy"
        elif rainfall > 2:
            condition = "cloudy"
        else:
            condition = "sunny"

        forecasts.append(DayForecast(
            date=d.isoformat(),
            temp_min_c=temp_min,
            temp_max_c=temp_max,
            humidity_percent=humidity,
            rainfall_mm=rainfall,
            wind_speed_kmh=wind,
            condition=condition,
        ))

    response = ForecastResponse(
        city=city_title,
        agro_climatic_zone=profile["zone"],
        generated_at=datetime.now().isoformat(),
        days=forecasts,
    )
    return response.model_dump()


@mcp.tool()
def get_soil_moisture(latitude: float, longitude: float) -> dict[str, Any]:
    """
    Return mock soil moisture and nutrient data for a geographic point.

    WHY: Soil moisture is the single most important input to irrigation scheduling.
    Combined with NPK levels, it lets the agent advise on both water AND fertiliser —
    the two biggest recurring costs for Indian farmers.

    Args:
        latitude: Latitude of the field (expected range: 8–37 for India).
        longitude: Longitude of the field (expected range: 68–97 for India).
    """
    log.info("get_soil_moisture called: lat=%.4f, lon=%.4f", latitude, longitude)

    # WHY: Soil type selection is based on latitude bands — a rough but useful proxy
    # for India's actual soil distribution (alluvial in north, black in central,
    # red/laterite in south).
    if latitude > 25:
        soil = SOIL_TYPES[0]  # Alluvial — Indo-Gangetic plains
    elif latitude > 20:
        soil = SOIL_TYPES[1]  # Black Cotton — Deccan
    elif latitude > 15:
        soil = SOIL_TYPES[2]  # Red Laterite — Southern peninsula
    else:
        soil = SOIL_TYPES[3]  # Sandy Loam — far south / coastal

    seed = f"{latitude:.2f}-{longitude:.2f}"
    today_seed = f"{seed}-{date.today().isoformat()}"

    response = SoilMoistureResponse(
        latitude=round(latitude, 4),
        longitude=round(longitude, 4),
        moisture_percent=_seeded_float(today_seed + "-moist", 15, 75),
        soil_type=soil["name"],
        ph_level=_seeded_float(seed + "-ph", soil["ph_range"][0], soil["ph_range"][1]),
        nitrogen_kg_ha=_seeded_float(seed + "-n", 120, 320),
        phosphorus_kg_ha=_seeded_float(seed + "-p", 10, 60),
        potassium_kg_ha=_seeded_float(seed + "-k", 100, 300),
        organic_carbon_percent=_seeded_float(seed + "-oc", soil["oc_range"][0], soil["oc_range"][1]),
    )
    return response.model_dump()


@mcp.tool()
def irrigation_rule(
    crop: str,
    soil_moisture_percent: float,
    forecast_rainfall_mm: float,
) -> dict[str, Any]:
    """
    Deterministic irrigation advice based on crop, soil moisture, and forecast rain.

    WHY: This is a *rule engine*, not an LLM opinion. Farmers and extension officers
    trust transparent, explainable logic for irrigation decisions. The rules encode
    best-practice thresholds from ICAR (Indian Council of Agricultural Research)
    guidelines. Keeping this deterministic also means it works identically even when
    MOCK_LLM=true — no model calls needed.

    Decision matrix:
    - soil_moisture < 30% AND forecast_rainfall < 5mm  → IRRIGATE
    - forecast_rainfall > 20mm                         → SKIP (rain will suffice)
    - soil_moisture >= 30% AND soil_moisture < 50%      → LIGHT irrigation if no rain
    - soil_moisture >= 50%                              → SKIP

    Args:
        crop: Crop name (e.g. rice, wheat, tomato).
        soil_moisture_percent: Current soil moisture (0–100).
        forecast_rainfall_mm: Total rainfall forecast for next 24–48 hours.
    """
    log.info(
        "irrigation_rule called: crop=%s, moisture=%.1f%%, rain=%.1fmm",
        crop, soil_moisture_percent, forecast_rainfall_mm,
    )

    crop_lower = crop.strip().lower()
    method = CROP_IRRIGATION_METHODS.get(crop_lower, DEFAULT_IRRIGATION_METHOD)

    # --- Decision logic ---
    should_irrigate: bool
    reason: str
    recommended_mm: float

    if forecast_rainfall_mm > 20.0:
        # WHY: Heavy rain expected — irrigating now wastes water and can waterlog fields.
        should_irrigate = False
        reason = (
            f"Heavy rainfall of {forecast_rainfall_mm:.0f}mm forecast. "
            "Skip irrigation to avoid waterlogging and save water."
        )
        recommended_mm = 0.0

    elif soil_moisture_percent < 30.0 and forecast_rainfall_mm < 5.0:
        # WHY: Critically dry soil with no rain relief — immediate irrigation needed.
        should_irrigate = True
        deficit = 50.0 - soil_moisture_percent  # target 50% field capacity
        recommended_mm = round(max(20.0, deficit * 1.2), 1)
        reason = (
            f"Soil moisture critically low at {soil_moisture_percent:.0f}% "
            f"with only {forecast_rainfall_mm:.0f}mm rain expected. "
            f"Irrigate {recommended_mm:.0f}mm via {method} method immediately."
        )

    elif soil_moisture_percent < 50.0 and forecast_rainfall_mm < 5.0:
        # WHY: Moderately dry — light irrigation prevents stress without waste.
        should_irrigate = True
        recommended_mm = round(max(10.0, (50.0 - soil_moisture_percent) * 0.8), 1)
        reason = (
            f"Soil moisture at {soil_moisture_percent:.0f}% (below optimal 50%). "
            f"Light rainfall of {forecast_rainfall_mm:.0f}mm won't suffice. "
            f"Apply {recommended_mm:.0f}mm via {method}."
        )

    else:
        # WHY: Adequate moisture or incoming rain — no irrigation needed.
        should_irrigate = False
        recommended_mm = 0.0
        if forecast_rainfall_mm >= 5.0:
            reason = (
                f"Soil moisture at {soil_moisture_percent:.0f}% and "
                f"{forecast_rainfall_mm:.0f}mm rainfall expected. No irrigation needed."
            )
        else:
            reason = (
                f"Soil moisture adequate at {soil_moisture_percent:.0f}%. "
                "No irrigation required."
            )

    advice = IrrigationAdvice(
        crop=crop_lower,
        should_irrigate=should_irrigate,
        reason=reason,
        recommended_mm=recommended_mm,
        method=method,
    )
    return advice.model_dump()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    port = int(os.environ.get("MCP_PORT", "8081"))

    log.info("Starting Weather MCP server: transport=%s, port=%d", transport, port)

    if transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
