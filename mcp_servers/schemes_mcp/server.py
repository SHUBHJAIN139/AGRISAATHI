"""
Government Schemes MCP Server for AgriSaathi.

WHY: Indian farmers are eligible for 50+ Central and State schemes but claim fewer
than 5 on average — not because they don't qualify, but because they don't *know*.
Scheme information is scattered across dozens of ministry websites in English/Hindi PDFs.
This server embeds a curated knowledge base of the 10 most impactful schemes and exposes
a simple keyword-search tool so the agent can instantly match a farmer's profile
(state, crop, land size) to relevant entitlements.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

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
log = logging.getLogger("schemes_mcp")

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "AgriSaathi Government Schemes MCP",
    description=(
        "Searches an embedded knowledge base of Indian government agricultural "
        "schemes and returns matching schemes with eligibility, benefits, and "
        "application details."
    ),
)

# ---------------------------------------------------------------------------
# Embedded Schemes Knowledge Base
# ---------------------------------------------------------------------------

# WHY: Embedding the KB directly in the server avoids an external database
# dependency — this is a read-only, infrequently-changing dataset. Updates happen
# via code deploys, which is acceptable for government scheme metadata that changes
# at most once per budget cycle (annually).

SCHEMES_KB: list[dict[str, Any]] = [
    {
        "id": "pm_kisan",
        "name": "PM-Kisan",
        "full_name": "Pradhan Mantri Kisan Samman Nidhi",
        "description": (
            "Direct income support of ₹6,000 per year to all landholding farmer "
            "families across the country, transferred in three equal installments "
            "of ₹2,000 every four months directly to bank accounts."
        ),
        "eligibility": [
            "All landholding farmer families (subject to exclusion criteria)",
            "Must have cultivable land in their name",
            "Excludes institutional landholders, former/current constitutional post holders",
            "Excludes income tax payers and professionals (doctors, engineers, lawyers, CAs)",
        ],
        "benefits": "₹6,000/year in 3 installments of ₹2,000 (Apr-Jul, Aug-Nov, Dec-Mar)",
        "documents_needed": [
            "Aadhaar card",
            "Land ownership records (Khatauni/Patta)",
            "Bank account with IFSC code",
            "Mobile number linked to Aadhaar",
        ],
        "how_to_apply": (
            "Apply online at pmkisan.gov.in or visit the nearest Common Service Centre (CSC). "
            "Village-level officials (Patwari/Revenue officer) can also register farmers. "
            "Self-registration available via PM-Kisan mobile app."
        ),
        "website": "https://pmkisan.gov.in",
        "helpline": "155261 / 011-24300606",
        "keywords": [
            "income", "cash", "money", "payment", "direct benefit", "dbt",
            "installment", "kisan samman", "pm kisan", "6000",
        ],
        "applicable_states": [],  # All states
        "applicable_crops": [],   # All crops
        "max_land_acres": 0,      # No upper limit
    },
    {
        "id": "pmfby",
        "name": "PMFBY",
        "full_name": "Pradhan Mantri Fasal Bima Yojana",
        "description": (
            "Comprehensive crop insurance scheme covering yield losses due to natural "
            "calamities, pests, and diseases. Premium rates are very low — 2% for Kharif, "
            "1.5% for Rabi, and 5% for horticulture/commercial crops — with the balance "
            "paid by Central and State governments."
        ),
        "eligibility": [
            "All farmers growing notified crops in notified areas",
            "Both loanee and non-loanee farmers (voluntary since Kharif 2020)",
            "Share-croppers and tenant farmers with documented agreement",
        ],
        "benefits": (
            "Kharif: farmer pays 2% premium. Rabi: 1.5%. Horticulture: 5%. "
            "Sum insured equals the cost of cultivation as fixed by the District Level "
            "Technical Committee. Claims settled based on Crop Cutting Experiments (CCE) "
            "and satellite/drone yield estimates."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Land records / tenancy agreement",
            "Bank account details",
            "Sowing declaration from Patwari/Agriculture Officer",
            "Premium payment receipt",
        ],
        "how_to_apply": (
            "Loanee farmers: automatically enrolled via bank at loan disbursement. "
            "Non-loanee: apply at bank branch, CSC, or pmfby.gov.in before the cut-off date. "
            "Use the 'Crop Insurance' mobile app for self-enrolment."
        ),
        "website": "https://pmfby.gov.in",
        "helpline": "1800-180-1551 (toll-free)",
        "keywords": [
            "insurance", "bima", "crop loss", "natural disaster", "flood",
            "drought", "hail", "pest", "fasal bima", "premium", "claim",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
    {
        "id": "kcc",
        "name": "KCC",
        "full_name": "Kisan Credit Card",
        "description": (
            "Provides farmers with affordable credit for crop production, post-harvest "
            "expenses, and consumption needs. Credit limit up to ₹3 lakh at 4% effective "
            "interest (7% base rate minus 3% interest subvention for timely repayment). "
            "Now extended to animal husbandry and fisheries farmers."
        ),
        "eligibility": [
            "Owner-cultivators, tenant farmers, sharecroppers, oral lessees",
            "Self Help Groups (SHGs) and Joint Liability Groups (JLGs)",
            "Animal husbandry and fisheries farmers (since 2019)",
            "No minimum land requirement",
        ],
        "benefits": (
            "Credit up to ₹3 lakh at 4% p.a. (with interest subvention for timely repayment). "
            "Crop insurance (PMFBY) and personal accident insurance (₹50,000) bundled. "
            "Flexible withdrawal via ATM-enabled RuPay card. "
            "Credit limit includes crop production + post-harvest + consumption + maintenance."
        ),
        "documents_needed": [
            "Aadhaar card and PAN card",
            "Land ownership / tenancy proof",
            "Passport-size photograph",
            "Bank application form",
            "Crop sowing plan / activity details",
        ],
        "how_to_apply": (
            "Apply at any commercial bank, cooperative bank, or Regional Rural Bank (RRB). "
            "Many banks offer online KCC application. PM-Kisan beneficiaries can apply via "
            "a simplified single-page form at their bank branch."
        ),
        "website": "https://www.pmkisan.gov.in/KCCForm.aspx",
        "helpline": "Contact your bank branch / Lead District Manager",
        "keywords": [
            "loan", "credit", "kcc", "kisan credit", "interest", "bank",
            "finance", "money", "borrow", "debt", "capital", "4 percent",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
    {
        "id": "soil_health_card",
        "name": "Soil Health Card",
        "full_name": "Soil Health Card Scheme",
        "description": (
            "Free soil testing for every farm with a printed Soil Health Card that shows "
            "nutrient status (N, P, K, S, Zn, Fe, Cu, Mn, Bo) and specific fertiliser "
            "recommendations for the crops being grown. Cards issued every 2 years."
        ),
        "eligibility": [
            "All farmers across India",
            "No land size restriction",
            "Available for both owned and leased land",
        ],
        "benefits": (
            "Free soil testing at government laboratories. "
            "Printed Soil Health Card with 12 soil parameters. "
            "Crop-specific fertiliser dose recommendations. "
            "Helps reduce fertiliser costs by 10-15% through balanced nutrition. "
            "Available in local languages."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Land details (survey number / khasra number)",
            "Village, block, and district information",
        ],
        "how_to_apply": (
            "Visit the nearest Krishi Vigyan Kendra (KVK), Agriculture Department office, "
            "or Soil Testing Laboratory. Soil samples can also be collected by trained "
            "village-level workers. Check card status at soilhealth.dac.gov.in."
        ),
        "website": "https://soilhealth.dac.gov.in",
        "helpline": "1800-180-1551 (toll-free)",
        "keywords": [
            "soil", "testing", "health", "nutrient", "fertiliser", "fertilizer",
            "npk", "soil card", "soil test", "ph", "nitrogen", "phosphorus",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
    {
        "id": "pm_kusum",
        "name": "PM-KUSUM",
        "full_name": "Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyaan",
        "description": (
            "Three-component solar energy scheme for farmers: (A) 10,000 MW solar plants "
            "on barren land, (B) standalone solar pumps up to 7.5 HP with up to 90% subsidy, "
            "(C) solarisation of existing grid-connected pumps. Farmers earn extra income by "
            "selling surplus solar power to DISCOMs."
        ),
        "eligibility": [
            "Component A: farmers/groups/cooperatives with barren or fallow land",
            "Component B: farmers in off-grid/water-scarce areas needing irrigation pumps",
            "Component C: farmers with existing grid-connected pumps",
            "Priority to small and marginal farmers",
        ],
        "benefits": (
            "Component B: 30% Central subsidy + 30% State subsidy + 30% bank loan = "
            "farmer pays only 10% for solar pump (up to 7.5 HP). "
            "Component C: solarise existing pump with 30% Central + 30% State subsidy. "
            "Surplus energy sold to DISCOM at pre-fixed tariff — extra income of ₹30,000-80,000/year."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Land ownership documents",
            "Existing electricity connection details (for Component C)",
            "Bank account details",
            "Photograph",
        ],
        "how_to_apply": (
            "Apply online at mnre.gov.in or through the State Renewable Energy Agency (SREDA). "
            "Contact the district agriculture officer or DISCOM for Component C. "
            "Some states have dedicated KUSUM portals."
        ),
        "website": "https://mnre.gov.in/solar/schemes",
        "helpline": "011-2436 0707 (MNRE)",
        "keywords": [
            "solar", "pump", "kusum", "energy", "electricity", "power",
            "solar pump", "irrigation pump", "subsidy", "renewable",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
    {
        "id": "midh",
        "name": "MIDH",
        "full_name": "Mission for Integrated Development of Horticulture",
        "description": (
            "Centrally sponsored scheme for holistic development of horticulture — "
            "covers fruits, vegetables, flowers, spices, mushrooms, medicinal plants, "
            "coconut, cashew, cocoa, and bamboo. Provides subsidy for planting material, "
            "drip irrigation, cold storage, and post-harvest infrastructure."
        ),
        "eligibility": [
            "All horticulture farmers",
            "Farmer Producer Organizations (FPOs)",
            "Entrepreneurs setting up post-harvest infrastructure",
            "Nurseries and seed producers",
        ],
        "benefits": (
            "40-50% subsidy on planting material and cultivation costs. "
            "55% subsidy on drip/sprinkler irrigation (for small/marginal farmers). "
            "35-50% subsidy on cold storage, ripening chambers, and pack houses. "
            "Up to ₹50,000/ha for new orchard establishment."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Land records",
            "Project proposal / cultivation plan",
            "Bank account details",
            "Caste certificate (for SC/ST/women — higher subsidy)",
        ],
        "how_to_apply": (
            "Apply through the District Horticulture Officer or State Horticulture Mission. "
            "Online applications via the National Horticulture Board (NHB) portal. "
            "Some states accept applications through DBT Agriculture portals."
        ),
        "website": "https://midh.gov.in",
        "helpline": "011-2338 2543 (NHB)",
        "keywords": [
            "horticulture", "fruit", "vegetable", "flower", "spice",
            "orchard", "plantation", "cold storage", "drip", "nursery",
            "mango", "banana", "guava", "citrus", "tomato", "onion",
        ],
        "applicable_states": [],
        "applicable_crops": [
            "tomato", "onion", "potato", "turmeric", "mango", "banana",
            "guava", "citrus", "flowers", "mushroom", "spices",
        ],
        "max_land_acres": 0,
    },
    {
        "id": "rkvy",
        "name": "RKVY",
        "full_name": "Rashtriya Krishi Vikas Yojana — Remunerative Approaches for "
                     "Agriculture and Allied Sector Rejuvenation",
        "description": (
            "Umbrella scheme that provides flexible funding to states for agriculture "
            "development projects. Covers infrastructure, value chains, agri-startups, "
            "and innovation. States design their own projects under RKVY guidelines."
        ),
        "eligibility": [
            "Individual farmers, FPOs, agri-entrepreneurs",
            "State governments and their agencies",
            "Agricultural universities and research institutes",
            "Agri-startups (under RKVY-RAFTAAR component)",
        ],
        "benefits": (
            "State-specific projects: farm mechanisation, watershed development, "
            "seed production, marketing infrastructure. "
            "RKVY-RAFTAAR: up to ₹25 lakh grant for agri-startups, incubation support, "
            "and mentoring. No fixed subsidy rate — varies by state and project."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Project proposal (for entrepreneurs/FPOs)",
            "Land/infrastructure details",
            "Bank account",
            "State-specific application form",
        ],
        "how_to_apply": (
            "Contact the State Agriculture Department or District Agriculture Officer. "
            "For RKVY-RAFTAAR (startups): apply at rkvy.nic.in. "
            "Proposals are evaluated at the State Level Sanctioning Committee (SLSC)."
        ),
        "website": "https://rkvy.nic.in",
        "helpline": "011-2338 2651 (DAC&FW)",
        "keywords": [
            "state scheme", "agriculture development", "infrastructure",
            "startup", "agri startup", "innovation", "mechanisation",
            "farm equipment", "watershed", "rkvy", "raftaar",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
    {
        "id": "nmsa",
        "name": "NMSA",
        "full_name": "National Mission for Sustainable Agriculture",
        "description": (
            "Promotes sustainable farming through soil health management, rainfed area "
            "development, climate change adaptation, and organic farming. Part of the "
            "National Action Plan on Climate Change (NAPCC)."
        ),
        "eligibility": [
            "All farmers, with priority to rainfed/dryland areas",
            "Farmers practising or willing to adopt organic/natural farming",
            "Farmer groups and FPOs for cluster-based projects",
            "Small and marginal farmers get higher subsidy rates",
        ],
        "benefits": (
            "Rainfed Area Development: ₹12,500/ha for integrated farming systems. "
            "Soil Health Management: free soil testing + ₹5,000/ha for organic inputs. "
            "Climate Change Adaptation: stress-tolerant seed varieties, water harvesting. "
            "Organic farming clusters: ₹10,000-50,000/ha over 3 years for PGS certification."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Land records",
            "Farmer registration with Agriculture Department",
            "Bank account details",
        ],
        "how_to_apply": (
            "Apply through the District Agriculture Officer or Block Development Officer. "
            "Some states have online portals under their Agriculture Department websites. "
            "Organic farming components via Paramparagat Krishi Vikas Yojana (PKVY) portal."
        ),
        "website": "https://nmsa.dac.gov.in",
        "helpline": "1800-180-1551 (toll-free)",
        "keywords": [
            "sustainable", "organic", "natural farming", "rainfed", "dryland",
            "climate", "soil health", "water conservation", "zero budget",
            "compost", "bio fertiliser", "green manure",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
    {
        "id": "enam",
        "name": "eNAM",
        "full_name": "Electronic National Agriculture Market",
        "description": (
            "Pan-India electronic trading platform that networks existing APMC mandis "
            "to create a unified national market. Farmers can see real-time prices across "
            "markets and sell to the highest bidder — even to buyers in other states. "
            "Eliminates middlemen and ensures transparent price discovery."
        ),
        "eligibility": [
            "Any farmer or FPO wishing to sell produce online",
            "Traders and buyers registered with any eNAM-linked mandi",
            "APMC-regulated commodities in eNAM-enabled states",
        ],
        "benefits": (
            "Free registration for farmers. "
            "Real-time prices from 1,000+ mandis nationwide. "
            "Online bidding — higher price discovery (5-10% improvement reported). "
            "E-payment directly to bank account within 24-48 hours. "
            "Quality assaying at mandi gate for fair grading. "
            "Reduced commission charges."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Bank account linked to Aadhaar",
            "Mobile number",
            "Mandi registration (can be done at the gate on first visit)",
        ],
        "how_to_apply": (
            "Register at the nearest eNAM-enabled mandi with Aadhaar and bank details. "
            "Download the eNAM mobile app for price tracking. "
            "Use the eNAM portal (enam.gov.in) for online lot posting and bid monitoring."
        ),
        "website": "https://enam.gov.in",
        "helpline": "1800-270-0224 (toll-free)",
        "keywords": [
            "enam", "online market", "mandi", "sell online", "price",
            "market price", "auction", "bidding", "apmc", "trade",
            "sell produce", "commission", "middleman",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
    {
        "id": "pmksy",
        "name": "PMKSY",
        "full_name": "Pradhan Mantri Krishi Sinchayee Yojana",
        "description": (
            "National mission for 'Har Khet Ko Paani' (water to every field) and "
            "'Per Drop More Crop' (micro-irrigation). Provides subsidies for drip "
            "irrigation, sprinkler systems, rainwater harvesting, and watershed "
            "development. Aims to expand cultivable area under assured irrigation."
        ),
        "eligibility": [
            "All farmers with cultivable land",
            "Priority to small/marginal farmers (< 2 hectares)",
            "Farmer groups / Water User Associations (WUAs)",
            "Available in all states (state co-funding required)",
        ],
        "benefits": (
            "Per Drop More Crop: 55% subsidy on micro-irrigation for small/marginal "
            "farmers (45% for others). Covers drip, sprinkler, micro-sprinkler, and "
            "rain-gun systems. "
            "Har Khet Ko Paani: canal lining, borewell recharge, farm ponds. "
            "Watershed Development: ₹12,000/ha for soil & water conservation."
        ),
        "documents_needed": [
            "Aadhaar card",
            "Land records (7/12 extract or Khatauni)",
            "Caste certificate (SC/ST get higher subsidy)",
            "Quotation from approved micro-irrigation supplier",
            "Bank account details",
            "Passport-size photograph",
        ],
        "how_to_apply": (
            "Apply at the District Agriculture Office or Block Development Office. "
            "Many states have online portals (e.g., GGRC in Gujarat, TANHODA in Tamil Nadu). "
            "Micro-irrigation subsidy often processed through Horticulture Department."
        ),
        "website": "https://pmksy.gov.in",
        "helpline": "1800-180-1551 (toll-free)",
        "keywords": [
            "irrigation", "drip", "sprinkler", "micro irrigation", "water",
            "sinchayee", "borewell", "farm pond", "rain water", "watershed",
            "per drop more crop", "har khet ko paani", "pipe", "pump",
        ],
        "applicable_states": [],
        "applicable_crops": [],
        "max_land_acres": 0,
    },
]


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class SchemeResult(BaseModel):
    """A single scheme search result."""
    name: str
    full_name: str
    description: str
    eligibility: list[str]
    benefits: str
    documents_needed: list[str]
    how_to_apply: str
    website: str
    helpline: str


class SearchResponse(BaseModel):
    """Top matching schemes from the knowledge base."""
    query: str
    filters_applied: dict[str, str]
    total_matches: int
    schemes: list[SchemeResult]


# ---------------------------------------------------------------------------
# Search logic
# ---------------------------------------------------------------------------

def _compute_relevance_score(
    scheme: dict[str, Any],
    query_tokens: set[str],
    state: str,
    land_acres: float,
    crop: str,
) -> float:
    """
    WHY: Simple keyword overlap scoring — no ML model needed for 10 schemes.
    The score is the fraction of query tokens that appear in the scheme's keyword
    list, description, or name. Bonus points for matching state, crop, and land
    eligibility filters. This is intentionally transparent and debuggable.
    """
    score = 0.0

    # --- Keyword matches ---
    scheme_text = " ".join([
        scheme["name"].lower(),
        scheme["full_name"].lower(),
        scheme["description"].lower(),
        " ".join(scheme["keywords"]),
    ])

    if not query_tokens:
        # No query → all schemes start with equal base score
        score = 1.0
    else:
        matching_tokens = sum(1 for t in query_tokens if t in scheme_text)
        score = matching_tokens / len(query_tokens) if query_tokens else 0.0

    # --- State filter bonus ---
    applicable_states = scheme.get("applicable_states", [])
    if state:
        state_lower = state.lower()
        if applicable_states:
            # If scheme has state restrictions, check match
            if any(state_lower in s.lower() for s in applicable_states):
                score += 0.3
            else:
                score -= 0.5  # Penalise non-matching state-specific schemes
        else:
            # Scheme available in all states — slight bonus for explicitly matching
            score += 0.1

    # --- Crop filter bonus ---
    applicable_crops = scheme.get("applicable_crops", [])
    if crop:
        crop_lower = crop.lower()
        if applicable_crops:
            if any(crop_lower in c.lower() for c in applicable_crops):
                score += 0.3
        # Also check if crop appears in keywords/description
        if crop_lower in scheme_text:
            score += 0.2

    # --- Land size filter ---
    max_land = scheme.get("max_land_acres", 0)
    if land_acres > 0 and max_land > 0:
        if land_acres <= max_land:
            score += 0.1
        else:
            score -= 0.3

    return score


@mcp.tool()
def search_schemes(
    query: str,
    state: str = "",
    land_acres: float = 0.0,
    crop: str = "",
) -> dict[str, Any]:
    """
    Search the embedded government schemes knowledge base.

    WHY: A farmer saying "I need help with irrigation cost" shouldn't have to know
    that PMKSY exists. This tool converts natural-language needs into scheme matches,
    bridging the awareness gap that keeps millions of farmers from claiming benefits
    they're entitled to. The search is keyword-based (no LLM needed) — fast, free,
    and deterministic.

    Args:
        query: Natural language query (e.g. "crop insurance", "solar pump subsidy",
               "loan for farming").
        state: Optional state filter (e.g. "Maharashtra", "Uttar Pradesh").
        land_acres: Optional land holding in acres for eligibility filtering.
        crop: Optional crop name to find crop-specific schemes.
    """
    log.info(
        "search_schemes called: query='%s', state='%s', land=%.1f, crop='%s'",
        query, state, land_acres, crop,
    )

    # Tokenise query — lowercase, split on spaces and common punctuation
    query_lower = query.strip().lower()
    query_tokens: set[str] = set()
    for token in query_lower.replace(",", " ").replace(".", " ").replace("?", " ").split():
        token = token.strip()
        if len(token) >= 2:  # skip single chars
            query_tokens.add(token)

    # Score every scheme
    scored: list[tuple[float, dict[str, Any]]] = []
    for scheme in SCHEMES_KB:
        score = _compute_relevance_score(scheme, query_tokens, state, land_acres, crop)
        if score > 0:
            scored.append((score, scheme))

    # Sort descending by score, take top 3
    scored.sort(key=lambda x: x[0], reverse=True)
    top_schemes = scored[:3]

    results: list[SchemeResult] = []
    for _score, scheme in top_schemes:
        results.append(SchemeResult(
            name=scheme["name"],
            full_name=scheme["full_name"],
            description=scheme["description"],
            eligibility=scheme["eligibility"],
            benefits=scheme["benefits"],
            documents_needed=scheme["documents_needed"],
            how_to_apply=scheme["how_to_apply"],
            website=scheme["website"],
            helpline=scheme["helpline"],
        ))

    filters_applied: dict[str, str] = {}
    if state:
        filters_applied["state"] = state
    if land_acres > 0:
        filters_applied["land_acres"] = str(land_acres)
    if crop:
        filters_applied["crop"] = crop

    response = SearchResponse(
        query=query,
        filters_applied=filters_applied,
        total_matches=len(scored),
        schemes=results,
    )
    return response.model_dump()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    port = int(os.environ.get("MCP_PORT", "8083"))

    log.info("Starting Government Schemes MCP server: transport=%s, port=%d", transport, port)

    if transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
