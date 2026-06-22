"""
AgriSaathi — WeatherAdvisor Agent
==================================
WHY: Indian agriculture is 60% rain-fed. A 7-day forecast with irrigation
advice can save an entire crop cycle. This agent connects weather data to
farming decisions — "should I irrigate today?" not just "will it rain?"

Architecture:
- Sub-agent of FarmerConcierge (root orchestrator)
- Connects to weather_mcp MCP server via McpToolset
- Tools: get_forecast, get_soil_moisture, irrigation_rule
- NO camera/vision tool (security constraint)

MCP Integration:
- In local dev (stdio): ADK launches weather_mcp as a subprocess
- In production (SSE): Connects to remote Cloud Run weather_mcp service
"""

from __future__ import annotations

import os

from google.adk.agents import Agent


# ---------------------------------------------------------------------------
# MCP Toolset Configuration
# ---------------------------------------------------------------------------
# WHY: We use McpToolset to connect to the weather MCP server.
# The MCP server exposes weather tools as standardized tool interfaces
# that the agent can call. This separation means the weather data source
# can be swapped (mock → IMD API → OpenWeather) without changing agent code.
# ---------------------------------------------------------------------------

def _get_weather_tools() -> list:
    """Build the tool list for WeatherAdvisor.

    WHY: Deferred import because McpToolset requires the mcp package,
    and we want the agent module to be importable even if mcp isn't installed
    (e.g., during test_imports.py startup checks).
    """
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "stdio":
        try:
            from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
            from google.adk.tools.mcp_tool import StdioConnectionParams
            from mcp import StdioServerParameters

            return [
                McpToolset(
                    connection_params=StdioConnectionParams(
                        server_params=StdioServerParameters(
                            command="python",
                            args=["-m", "mcp_servers.weather_mcp.server"],
                        ),
                        timeout=30,
                    ),
                )
            ]
        except ImportError:
            pass

    # Fallback: return empty tools list (agent will work without MCP in test mode)
    return []


# ---------------------------------------------------------------------------
# Agent Definition
# ---------------------------------------------------------------------------
WEATHER_ADVISOR_INSTRUCTION = """You are WeatherAdvisor (मौसम सलाहकार), an agricultural 
meteorology expert AI agent. Your role is to provide weather forecasts and 
irrigation advice tailored to farming decisions.

BEHAVIOR:
1. When asked about weather, use `get_forecast` to fetch the 7-day forecast.
2. When asked about irrigation, first get soil moisture with `get_soil_moisture`, 
   then get the forecast, then call `irrigation_rule` to get a recommendation.
3. Present weather in farmer-friendly terms:
   - "अगले 3 दिन बारिश होगी, सिंचाई मत करो" (Don't irrigate, rain coming)
   - "मिट्टी सूखी है, आज शाम को पानी दो" (Soil is dry, water this evening)
4. Always mention extreme weather warnings (heat wave, heavy rain, frost).
5. Connect weather to crop-specific risks (e.g., "humidity > 80% + rain = late blight risk for tomato").

RESPONSE FORMAT (adapt to farmer's language):
🌤️ **आज का मौसम / Today's Weather:** [summary]
📅 **7-दिन पूर्वानुमान / 7-Day Forecast:** [brief daily summary]
💧 **सिंचाई सलाह / Irrigation Advice:** [irrigate or skip + reason]
⚠️ **चेतावनी / Alerts:** [extreme weather warnings if any]

CONSTRAINTS:
- You CANNOT analyze crop photos. Do not accept image inputs.
- You CANNOT look up mandi prices or government schemes.
- If asked about non-weather topics, politely redirect to the appropriate agent.
- Use metric units (°C, mm, km/h).
"""

weather_advisor_agent = Agent(
    name="weather_advisor",
    model=os.environ.get("LLM_MODEL", "gemini-2.0-flash"),
    description=(
        "Provides 7-day weather forecasts and irrigation advice for Indian farmers. "
        "Uses soil moisture data and rainfall predictions to recommend when and how much "
        "to irrigate. Warns about extreme weather risks to crops. "
        "Use this agent when a farmer asks about weather, rain, irrigation, or watering."
    ),
    instruction=WEATHER_ADVISOR_INSTRUCTION,
    tools=_get_weather_tools(),
)
