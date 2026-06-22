"""
Mandi (Market) Price MCP Server for AgriSaathi.

WHY: Price discovery is the #1 pain point for Indian farmers. Middlemen exploit
information asymmetry — the farmer doesn't know what the same crop fetches 50km away.
This server mirrors the eNAM (electronic National Agriculture Market) data model and
gives the agent real-time-like price intelligence, trend analysis, and sell/hold
recommendations so the farmer can negotiate from a position of knowledge.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging — stderr only (stdout is the JSON-RPC transport)
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("mandi_mcp")

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "AgriSaathi Mandi MCP",
    description=(
        "Provides mandi (market) prices, 7-day trend analysis, and "
        "sell/hold recommendations for Indian agricultural commodities."
    ),
)

# ---------------------------------------------------------------------------
# Constants — Commodity base prices and market metadata
# ---------------------------------------------------------------------------

# WHY: Base prices are calibrated to real eNAM modal prices (June 2025 range).
# The spread (min/max around modal) reflects actual auction variability at APMCs.
COMMODITY_PRICES: dict[str, dict[str, Any]] = {
    "wheat": {"modal": 2500, "spread": 200, "unit": "₹/quintal", "season": "rabi"},
    "rice": {"modal": 3800, "spread": 300, "unit": "₹/quintal", "season": "kharif"},
    "tomato": {"modal": 2200, "spread": 800, "unit": "₹/quintal", "season": "all"},
    "onion": {"modal": 1800, "spread": 600, "unit": "₹/quintal", "season": "all"},
    "potato": {"modal": 1200, "spread": 400, "unit": "₹/quintal", "season": "rabi"},
    "cotton": {"modal": 6800, "spread": 500, "unit": "₹/quintal", "season": "kharif"},
    "soybean": {"modal": 4600, "spread": 400, "unit": "₹/quintal", "season": "kharif"},
    "mustard": {"modal": 5200, "spread": 350, "unit": "₹/quintal", "season": "rabi"},
    "sugarcane": {"modal": 350, "spread": 30, "unit": "₹/quintal", "season": "all"},
    "turmeric": {"modal": 12500, "spread": 1500, "unit": "₹/quintal", "season": "kharif"},
}

# WHY: Market names map to actual APMC mandis. The city tag lets the agent cross-
# reference with weather data for logistics advice (e.g., "don't transport during
# heavy rain in Mumbai").
MARKETS: dict[str, dict[str, str]] = {
    "Azadpur": {"city": "Delhi", "state": "Delhi"},
    "Vashi": {"city": "Mumbai", "state": "Maharashtra"},
    "Koyambedu": {"city": "Chennai", "state": "Tamil Nadu"},
    "Koley Market": {"city": "Kolkata", "state": "West Bengal"},
    "Yeshwanthpur": {"city": "Bengaluru", "state": "Karnataka"},
    "Bowenpally": {"city": "Hyderabad", "state": "Telangana"},
    "Chomu": {"city": "Jaipur", "state": "Rajasthan"},
    "Amausi": {"city": "Lucknow", "state": "Uttar Pradesh"},
}

# WHY: Nearby-market recommendations need a lookup. In reality this would be
# a geo-distance query, but for the mock we hard-code logical pairings.
NEARBY_MARKETS: dict[str, str] = {
    "Azadpur": "Ghazipur Mandi (Delhi)",
    "Vashi": "Turbhe APMC (Navi Mumbai)",
    "Koyambedu": "Perambur Market (Chennai)",
    "Koley Market": "Sealdah Market (Kolkata)",
    "Yeshwanthpur": "Ramanagara APMC (Karnataka)",
    "Bowenpally": "Gaddiannaram (Hyderabad)",
    "Chomu": "Muhana Mandi (Jaipur)",
    "Amausi": "Alambagh Mandi (Lucknow)",
}


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class MandiPriceResponse(BaseModel):
    """Today's price snapshot for a commodity at a specific mandi."""
    commodity: str
    market: str
    market_city: str
    market_state: str
    date: str
    price_per_quintal: float
    min_price: float
    max_price: float
    modal_price: float
    unit: str
    arrivals_tonnes: float


class DayPrice(BaseModel):
    """Single day's price in a trend series."""
    date: str
    price: float


class TrendResponse(BaseModel):
    """7-day price trend with analysis."""
    commodity: str
    market: str
    prices: list[DayPrice]
    trend: Literal["rising", "falling", "stable"]
    change_percent: float
    avg_price: float


class RecommendationResponse(BaseModel):
    """Sell/hold/wait recommendation."""
    commodity: str
    market: str
    action: Literal["sell_now", "hold", "wait_for_better"]
    confidence: float
    reason: str
    estimated_revenue: float
    best_market_nearby: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seeded_float(seed: str, low: float, high: float) -> float:
    """
    WHY: Deterministic pseudo-random — same inputs always produce same output
    for reproducible agent testing and demo stability.
    """
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    fraction = (h % 10000) / 10000.0
    return round(low + fraction * (high - low), 2)


def _normalise_commodity(raw: str) -> str | None:
    """Case-insensitive commodity lookup."""
    key = raw.strip().lower()
    return key if key in COMMODITY_PRICES else None


def _normalise_market(raw: str) -> str | None:
    """Case-insensitive market lookup (matches on substring too)."""
    raw_lower = raw.strip().lower()
    for m in MARKETS:
        if raw_lower == m.lower() or raw_lower in m.lower():
            return m
    return None


def _day_price(commodity: str, market: str, d: date) -> float:
    """Generate a stable mock price for a commodity-market-date triple."""
    base = COMMODITY_PRICES[commodity]["modal"]
    spread = COMMODITY_PRICES[commodity]["spread"]
    seed = f"{commodity}-{market}-{d.isoformat()}"
    return _seeded_float(seed, base - spread, base + spread)


def _arrivals(commodity: str, market: str, d: date) -> float:
    """Mock daily arrivals in tonnes — larger mandis get more volume."""
    seed = f"arr-{commodity}-{market}-{d.isoformat()}"
    # WHY: Azadpur is Asia's largest; others scale down.
    multiplier = 2.0 if market == "Azadpur" else 1.0
    return round(_seeded_float(seed, 50, 500) * multiplier, 1)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_mandi_price(commodity: str, market: str) -> dict[str, Any]:
    """
    Return today's price for a commodity at a specific mandi (APMC market).

    WHY: Farmers decide whether to load their tractor and drive to the mandi based
    on today's price. Even a ₹50/quintal difference on 20 quintals of wheat is ₹1000
    — a meaningful sum for a smallholder. This tool gives the agent the price snapshot
    it needs for sell/hold advice.

    Args:
        commodity: Crop/produce name (e.g. wheat, rice, tomato).
        market: Mandi name (e.g. Azadpur, Vashi, Koyambedu).
    """
    log.info("get_mandi_price called: commodity=%s, market=%s", commodity, market)

    norm_commodity = _normalise_commodity(commodity)
    if norm_commodity is None:
        supported = ", ".join(sorted(COMMODITY_PRICES))
        return {"error": f"Unsupported commodity '{commodity}'. Supported: {supported}"}

    norm_market = _normalise_market(market)
    if norm_market is None:
        supported = ", ".join(sorted(MARKETS))
        return {"error": f"Unsupported market '{market}'. Supported: {supported}"}

    today = date.today()
    modal = _day_price(norm_commodity, norm_market, today)
    spread = COMMODITY_PRICES[norm_commodity]["spread"]

    response = MandiPriceResponse(
        commodity=norm_commodity,
        market=norm_market,
        market_city=MARKETS[norm_market]["city"],
        market_state=MARKETS[norm_market]["state"],
        date=today.isoformat(),
        price_per_quintal=modal,
        min_price=round(modal - spread * 0.4, 2),
        max_price=round(modal + spread * 0.35, 2),
        modal_price=modal,
        unit=COMMODITY_PRICES[norm_commodity]["unit"],
        arrivals_tonnes=_arrivals(norm_commodity, norm_market, today),
    )
    return response.model_dump()


@mcp.tool()
def get_7day_trend(commodity: str, market: str) -> dict[str, Any]:
    """
    Return 7-day price history with trend analysis for a commodity at a mandi.

    WHY: A single day's price is noise; the *trend* is the signal. A farmer holding
    50 quintals of onion needs to know if prices are rising (hold for better returns)
    or crashing (sell before it drops further). This tool converts raw price series
    into an actionable trend label.

    Args:
        commodity: Crop/produce name.
        market: Mandi name.
    """
    log.info("get_7day_trend called: commodity=%s, market=%s", commodity, market)

    norm_commodity = _normalise_commodity(commodity)
    if norm_commodity is None:
        supported = ", ".join(sorted(COMMODITY_PRICES))
        return {"error": f"Unsupported commodity '{commodity}'. Supported: {supported}"}

    norm_market = _normalise_market(market)
    if norm_market is None:
        supported = ", ".join(sorted(MARKETS))
        return {"error": f"Unsupported market '{market}'. Supported: {supported}"}

    today = date.today()
    prices: list[DayPrice] = []
    price_values: list[float] = []

    for i in range(6, -1, -1):  # 6 days ago → today
        d = today - timedelta(days=i)
        p = _day_price(norm_commodity, norm_market, d)
        prices.append(DayPrice(date=d.isoformat(), price=p))
        price_values.append(p)

    # Trend detection — compare first half average to second half average
    first_half_avg = sum(price_values[:3]) / 3
    second_half_avg = sum(price_values[4:]) / 3  # last 3 days
    avg_price = round(sum(price_values) / len(price_values), 2)

    change_percent = round(((second_half_avg - first_half_avg) / first_half_avg) * 100, 2)

    if change_percent > 3.0:
        trend: Literal["rising", "falling", "stable"] = "rising"
    elif change_percent < -3.0:
        trend = "falling"
    else:
        trend = "stable"

    response = TrendResponse(
        commodity=norm_commodity,
        market=norm_market,
        prices=prices,
        trend=trend,
        change_percent=change_percent,
        avg_price=avg_price,
    )
    return response.model_dump()


@mcp.tool()
def recommend_action(
    commodity: str,
    market: str,
    quantity_quintals: float,
) -> dict[str, Any]:
    """
    Recommend sell/hold/wait based on 7-day price trend for a commodity.

    WHY: The raw trend data is useful for data-literate users, but most Indian
    smallholders want a clear directive: "sell now" or "wait". This tool wraps
    the trend analysis into a single actionable recommendation with an estimated
    revenue figure — the number that actually matters to the farmer.

    Decision rules:
    - Trend rising → hold (prices improving, wait for peak)
    - Trend falling → sell_now (cut losses before further drop)
    - Trend stable AND current price > average → sell_now (good price, take it)
    - Trend stable AND current price ≤ average → wait_for_better

    Args:
        commodity: Crop/produce name.
        market: Mandi name.
        quantity_quintals: Amount to sell (in quintals, 1 quintal = 100kg).
    """
    log.info(
        "recommend_action called: commodity=%s, market=%s, qty=%.1f",
        commodity, market, quantity_quintals,
    )

    # Reuse trend analysis
    trend_data = get_7day_trend(commodity, market)
    if "error" in trend_data:
        return trend_data

    trend = trend_data["trend"]
    avg_price = trend_data["avg_price"]
    current_price = trend_data["prices"][-1]["price"]  # today's price
    change_pct = trend_data["change_percent"]

    norm_market = _normalise_market(market)
    nearby = NEARBY_MARKETS.get(norm_market or "", "Check nearby APMC on eNAM portal")

    action: Literal["sell_now", "hold", "wait_for_better"]
    confidence: float
    reason: str

    if trend == "rising":
        action = "hold"
        confidence = 0.75
        reason = (
            f"Prices are rising ({change_pct:+.1f}% over 7 days). "
            f"Current ₹{current_price:.0f}/qtl vs avg ₹{avg_price:.0f}/qtl. "
            "Hold for 3-5 more days for potentially better returns."
        )
    elif trend == "falling":
        action = "sell_now"
        confidence = 0.82
        reason = (
            f"Prices are falling ({change_pct:+.1f}% over 7 days). "
            f"Current ₹{current_price:.0f}/qtl and declining. "
            "Sell immediately to minimize losses. Check nearby markets for better rates."
        )
    elif current_price > avg_price:
        action = "sell_now"
        confidence = 0.70
        reason = (
            f"Prices stable but currently above 7-day average "
            f"(₹{current_price:.0f} vs ₹{avg_price:.0f}). "
            "Good time to sell at above-average rates."
        )
    else:
        action = "wait_for_better"
        confidence = 0.60
        reason = (
            f"Prices stable but currently at/below average "
            f"(₹{current_price:.0f} vs ₹{avg_price:.0f}). "
            "Wait a few days — prices may improve. Monitor daily."
        )

    estimated_revenue = round(current_price * quantity_quintals, 2)

    response = RecommendationResponse(
        commodity=trend_data["commodity"],
        market=trend_data["market"],
        action=action,
        confidence=confidence,
        reason=reason,
        estimated_revenue=estimated_revenue,
        best_market_nearby=nearby,
    )
    return response.model_dump()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    port = int(os.environ.get("MCP_PORT", "8082"))

    log.info("Starting Mandi MCP server: transport=%s, port=%d", transport, port)

    if transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
