"""
AgriSaathi — MarketWhisperer Agent
====================================
WHY: Indian farmers lose ₹90,000 crore annually to information asymmetry
in agricultural markets. A farmer selling tomatoes in Azadpur mandi has no
idea that Vashi mandi is paying ₹500/quintal more. This agent bridges that
information gap with real-time price data and sell/hold recommendations.

Architecture:
- Sub-agent of FarmerConcierge (root orchestrator)
- Connects to mandi_mcp MCP server via McpToolset
- Tools: get_mandi_price, get_7day_trend, recommend_action
- NO camera/vision tool (security constraint — cannot see photos)

MCP Integration:
- In local dev (stdio): ADK launches mandi_mcp as a subprocess
- In production (SSE): Connects to remote Cloud Run mandi_mcp service
"""

from __future__ import annotations

import os

from google.adk.agents import Agent


# ---------------------------------------------------------------------------
# MCP Toolset Configuration
# ---------------------------------------------------------------------------
def _get_mandi_tools() -> list:
    """Build the tool list for MarketWhisperer.

    WHY: Same deferred-import pattern as WeatherAdvisor. MCP tools are loaded
    at runtime to keep the agent importable during startup checks.
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
                            args=["-m", "mcp_servers.mandi_mcp.server"],
                        ),
                        timeout=30,
                    ),
                )
            ]
        except ImportError:
            pass

    return []


# ---------------------------------------------------------------------------
# Agent Definition
# ---------------------------------------------------------------------------
MARKET_WHISPERER_INSTRUCTION = """You are MarketWhisperer (बाज़ार गुरु), an agricultural 
market intelligence AI agent. Your role is to help farmers get the best price 
for their produce by providing real-time mandi prices and sell/hold advice.

BEHAVIOR:
1. When asked about prices, use `get_mandi_price` to fetch today's price.
2. For trend analysis, use `get_7day_trend` to show price movement.
3. For sell/hold advice, use `recommend_action` with the farmer's quantity.
4. Always compare prices across nearby mandis when possible.
5. Present prices in ₹/quintal (standard Indian agricultural unit).
6. Explain trends in simple terms: "भाव बढ़ रहे हैं" (prices are rising).

RESPONSE FORMAT (adapt to farmer's language):
📊 **आज का भाव / Today's Price:**
- [commodity] in [market]: ₹[price]/quintal
- Min: ₹[min] | Max: ₹[max] | Modal: ₹[modal]

📈 **7-दिन का रुझान / 7-Day Trend:** [rising/falling/stable] ([X]% change)

💡 **सलाह / Recommendation:** [sell now / hold / wait]
- कारण / Reason: [explanation in simple terms]
- अनुमानित आय / Estimated Revenue: ₹[amount] for [quantity] quintals

🏪 **बेहतर मंडी / Better Market Nearby:** [if applicable]

CONSTRAINTS:
- You CANNOT analyze crop photos. Do not accept image inputs.
- You CANNOT provide weather forecasts or government scheme information.
- If asked about non-market topics, politely redirect to the appropriate agent.
- Always use ₹ (INR) for prices.
- 1 quintal = 100 kg. Always clarify the unit.
"""

market_whisperer_agent = Agent(
    name="market_whisperer",
    model=os.environ.get("LLM_MODEL", "gemini-2.0-flash"),
    description=(
        "Provides real-time mandi (market) prices for agricultural commodities, "
        "7-day price trend analysis, and sell/hold recommendations for Indian farmers. "
        "Compares prices across nearby mandis to maximize farmer revenue. "
        "Use this agent when a farmer asks about crop prices, selling produce, or market trends."
    ),
    instruction=MARKET_WHISPERER_INSTRUCTION,
    tools=_get_mandi_tools(),
)
