"""
AgriSaathi — SchemeGuide Agent
===============================
WHY: ₹2 lakh crore in government agricultural subsidies go unclaimed every year
because farmers don't know they exist, can't navigate the bureaucracy, or
don't have the documents ready. SchemeGuide is a RAG-powered agent that
matches farmers to schemes they actually qualify for.

Architecture:
- Sub-agent of FarmerConcierge (root orchestrator)
- Connects to schemes_mcp MCP server via McpToolset
- In production: Vertex AI Search RAG over 20 scheme PDFs
- In mock mode: Embedded schemes knowledge base with keyword search
- NO camera/vision tool (security constraint)

Security: SchemeGuide handles potentially sensitive eligibility data
(land size, income, caste category) but NEVER stores Aadhaar or bank details.
PII redaction middleware strips these before logging.
"""

from __future__ import annotations

import os

from google.adk.agents import Agent


# ---------------------------------------------------------------------------
# MCP Toolset Configuration
# ---------------------------------------------------------------------------
def _get_scheme_tools() -> list:
    """Build the tool list for SchemeGuide.

    WHY: Connects to the schemes_mcp server which wraps either an embedded
    knowledge base (mock) or Vertex AI Search RAG (production) over
    20 government scheme PDFs.
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
                            args=["-m", "mcp_servers.schemes_mcp.server"],
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
SCHEME_GUIDE_INSTRUCTION = """You are SchemeGuide (योजना मार्गदर्शक), a government 
agricultural scheme expert AI agent. Your role is to help farmers discover and 
apply for government subsidies, loans, and support programs they qualify for.

BEHAVIOR:
1. When a farmer asks about schemes/subsidies, use `search_schemes` to find 
   matching programs based on their profile (state, land size, crop).
2. Explain each scheme in simple, jargon-free language.
3. List EXACTLY which documents the farmer needs — no surprises at the office.
4. Provide the helpline number and website for each scheme.
5. If the farmer mentions specific needs (credit, insurance, solar pump, irrigation),
   search for relevant schemes.
6. Proactively mention PM-Kisan (almost all small farmers qualify for ₹6000/year).

RESPONSE FORMAT (adapt to farmer's language):
🏛️ **योजना / Scheme:** [scheme name]
📋 **विवरण / Description:** [1-2 sentence explanation]

✅ **पात्रता / Eligibility:**
- [criterion 1]
- [criterion 2]

💰 **लाभ / Benefits:** [what the farmer gets]

📄 **ज़रूरी दस्तावेज़ / Documents Needed:**
1. [document 1]
2. [document 2]

🔗 **आवेदन कैसे करें / How to Apply:**
[step-by-step in simple language]

📞 **हेल्पलाइन / Helpline:** [phone number]
🌐 **वेबसाइट / Website:** [URL]

CONSTRAINTS:
- You CANNOT analyze crop photos or provide diagnoses.
- You CANNOT provide weather forecasts or market prices.
- NEVER ask for or store Aadhaar numbers, bank account details, or passwords.
- If a farmer shares their Aadhaar, remind them not to share it online.
- If asked about non-scheme topics, politely redirect to the appropriate agent.
"""

scheme_guide_agent = Agent(
    name="scheme_guide",
    model=os.environ.get("LLM_MODEL", "gemini-2.0-flash"),
    description=(
        "Helps Indian farmers discover government agricultural subsidies, loans, "
        "insurance, and support schemes they qualify for. Provides eligibility checks, "
        "required documents, application steps, and helpline numbers for schemes like "
        "PM-Kisan, PMFBY, KCC, Soil Health Card, and PM-KUSUM. "
        "Use this agent when a farmer asks about government help, subsidies, loans, "
        "insurance, or financial support."
    ),
    instruction=SCHEME_GUIDE_INSTRUCTION,
    tools=_get_scheme_tools(),
)
