"""
AgriSaathi — CropDoctor Agent
==============================
WHY: Diagnoses crop diseases from leaf photographs using Gemini 2.0 Flash
multimodal vision. This is the primary value proposition for farmers who
lack access to agronomists — a single photo replaces a 50km trip.

Architecture:
- Sub-agent of FarmerConcierge (root orchestrator)
- Uses vision_tool.analyze_crop_image for photo analysis
- Returns structured CropDiagnosis with treatment + organic alternatives
- Has camera/vision capability (unlike WeatherAdvisor, MarketWhisperer, SchemeGuide)

Security: This is the ONLY agent with vision tool access.
"""

from __future__ import annotations

import os
from typing import Any

from google.adk.agents import Agent
from google.genai import types

from tools.vision_tool import analyze_crop_image, CropDiagnosis


# ---------------------------------------------------------------------------
# WHY: Wraps the vision tool as an ADK-compatible function tool.
# ADK requires tools to be plain functions (not Pydantic methods).
# ---------------------------------------------------------------------------
def diagnose_crop_disease(
    image_base64: str,
    image_filename: str | None = None,
) -> dict[str, Any]:
    """Analyze a crop leaf photo to diagnose disease and recommend treatment.

    WHY this tool exists: 600M Indian farmers lose 30-40% of crops to disease
    every year. Most have no agronomist within 50km. This tool gives them an
    instant diagnosis from a phone camera photo, in their own language.

    Args:
        image_base64: Base64-encoded image data from the farmer's phone camera.
        image_filename: Optional original filename. Used in mock mode to match
            PlantVillage ground truth labels (e.g., 'Tomato___Late_blight_001.jpg').

    Returns:
        dict with keys: disease, confidence, crop_name, treatment,
        organic_alternative, organic_treatment, severity.
    """
    diagnosis: CropDiagnosis = analyze_crop_image(
        image_base64=image_base64,
        image_filename=image_filename,
    )
    return diagnosis.model_dump()


# ---------------------------------------------------------------------------
# Agent Definition
# ---------------------------------------------------------------------------
CROP_DOCTOR_INSTRUCTION = """You are CropDoctor (फसल डॉक्टर), an expert agricultural 
pathologist AI agent. Your role is to diagnose crop diseases from leaf photographs 
and recommend treatments.

BEHAVIOR:
1. When a farmer shares a photo of a diseased leaf, use the `diagnose_crop_disease` 
   tool to analyze it.
2. Always present results in the farmer's language (detect from conversation context).
3. ALWAYS recommend organic treatment FIRST if available. Chemical treatment is a 
   fallback — many smallholder farmers cannot afford pesticides.
4. Be empathetic. These farmers' livelihoods depend on your accuracy.
5. If confidence < 0.7, say so honestly and recommend visiting a Krishi Vigyan Kendra.
6. Include severity level and urgency of treatment.
7. For healthy crops, congratulate the farmer and give preventive tips.

RESPONSE FORMAT (adapt to farmer's language):
🌿 **फसल / Crop:** [crop name]
🔬 **रोग / Disease:** [disease name]  
📊 **विश्वास / Confidence:** [X]%
⚠️ **गंभीरता / Severity:** [low/medium/high/critical]

🌱 **जैविक उपचार / Organic Treatment (recommended):**
[organic treatment details]

💊 **रासायनिक उपचार / Chemical Treatment (if organic fails):**
[chemical treatment details]

⏰ **कब करें / When to apply:** [timing advice]

CONSTRAINTS:
- You can ONLY analyze crop images. Do not answer weather, price, or scheme questions.
- If asked about non-crop topics, politely redirect to the appropriate agent.
- Never fabricate a diagnosis. If unsure, say so.
"""

# WHY: CropDoctor is the only agent with vision capability.
# Other agents (WeatherAdvisor, MarketWhisperer, SchemeGuide) are
# explicitly denied camera access as a security control.
crop_doctor_agent = Agent(
    name="crop_doctor",
    model=os.environ.get("VISION_MODEL", "gemini-2.0-flash"),
    description=(
        "Analyzes crop leaf photographs to diagnose plant diseases. "
        "Returns disease identification, confidence score, treatment plan "
        "with organic-first recommendations, and severity assessment. "
        "Use this agent when a farmer shares a photo of a diseased or damaged crop leaf."
    ),
    instruction=CROP_DOCTOR_INSTRUCTION,
    tools=[diagnose_crop_disease],
)
