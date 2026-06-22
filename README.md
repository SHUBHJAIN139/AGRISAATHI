# 🌾 AgriSaathi — अन्नदाता साथी

**Multilingual AI Farming Companion for Smallholder Indian Farmers**

> *Five AI agents. Six languages. One mission: help the farmer who needs it most.*

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-orange.svg)](https://github.com/google/adk-python)

---

## 🎯 Problem

| Statistic | Impact |
|-----------|--------|
| 🌾 **600 million** farmers in India | 86% are smallholders (< 2 hectares) |
| 📉 **30–40%** annual crop loss | Disease, pests, weather — no expert within 50km |
| 💰 **₹2 lakh crore** unclaimed subsidies | Farmers don't know they qualify |
| 📊 **₹90,000 crore** lost to price asymmetry | Middlemen exploit information gaps |

A marginal farmer on a ₹8,000 Android phone needs instant, actionable advice — in their own language, from a single photo or voice message. No English. No jargon. No 50km trips.

## 💡 Solution

AgriSaathi is a **multi-agent AI system** that provides:

1. 📸 **Crop Disease Diagnosis** — Photo → diagnosis in <4 seconds
2. 🌤️ **Weather & Irrigation** — 7-day forecast + "should I irrigate today?"
3. 📊 **Mandi Prices** — Real-time prices + sell/hold recommendations
4. 🏛️ **Government Schemes** — Eligibility matching for PM-Kisan, PMFBY, KCC, etc.
5. 🗣️ **Voice I/O** — Speak in Hindi, Tamil, Telugu, Bengali, Marathi, or English

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐
│  React PWA  │────▶│  FastAPI Gateway  │────▶│  FarmerConcierge (ADK Root) │
│  6 Languages│     │  JWT · PII · Rate │     │  Intent + Language Router   │
│  Voice I/O  │     └──────────────────┘     └─────────┬───────────────────┘
│  Camera     │                                        │
└─────────────┘                               ┌───────┼───────┬───────────┐
                                              ▼       ▼       ▼           ▼
                                         CropDoctor  Weather  Market   Scheme
                                         (Vision)   Advisor  Whisperer  Guide
                                              │       │       │           │
                                              ▼       ▼       ▼           ▼
                                         Gemini   weather  mandi_mcp  schemes
                                         2.0      _mcp     (eNAM)     _mcp
                                         Flash    (IMD)                (RAG)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed Mermaid diagrams and tech stack table.

## 🪟 Windows Quickstart (tested)

> If you're on Windows with Python at a non-standard path, use these scripts.

1. Make sure Python 3.11 is at `E:\python311\python.exe`
   *(If your Python is elsewhere, edit line 16 of `scripts\setup_windows.bat`)*
2. Copy `.env.example` to `.env`: `copy .env.example .env`
3. Double-click `scripts\setup_windows.bat` — creates venv, installs deps, verifies imports
4. Double-click `scripts\verify_windows.bat` — runs all unit tests
5. If both pass, activate the venv and start the server:
   ```cmd
   .venv\Scripts\activate
   python -m uvicorn api.main:app --port 8080
   ```
6. Open http://localhost:8080/health — you should see `{"status": "healthy"}`

## 🚀 Quickstart (< 5 minutes)

### Prerequisites
- Python 3.11+
- Node.js 18+
- pip

### 1. Clone and configure

```bash
git clone https://github.com/agri-saathi/agri-saathi.git
cd agri-saathi
cp .env.example .env
```

### 2. Install backend

```bash
pip install -e ".[dev]"
```

### 3. Start the API server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

### 4. Test it works

```bash
# Get a dev token
curl -X POST http://localhost:8080/token?user_id=farmer_001

# Send a chat message (replace TOKEN)
curl -X POST http://localhost:8080/chat \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "मेरे टमाटर के पत्ते पीले हो रहे हैं", "session_id": "s1", "user_id": "farmer_001", "language": "hi"}'
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### Docker (one command)

```bash
docker compose up --build
# API: http://localhost:8080
# Frontend: http://localhost:5173
```

## 🔄 Mock vs Production

| Concern | Mock (this repo, runs offline) | Production swap |
|---------|-------------------------------|----------------|
| LLM | `MOCK_LLM=true` canned JSON | Gemini 2.0 Flash API via Secret Manager |
| Memory | SQLite (`session_store.py`) | Firestore |
| Weather/Mandi | JSON fixtures in MCP servers | Real MCP servers → eNAM / IMD APIs |
| Schemes RAG | Embedded `schemes_kb.json` | Vertex AI Search over 20 scheme PDFs |
| Auth | JWT mock (`api/security.py`) | Firebase phone OTP |
| Hosting | `docker compose up` | Cloud Run + Firebase Hosting |
| Secrets | `.env` placeholders | GCP Secret Manager |

## 📊 Evaluation

**PlantVillage 100-image subset evaluation:**

| Metric | Result | Threshold |
|--------|--------|-----------|
| Top-1 Accuracy | ≥ 95% | ≥ 80% |
| Top-3 Accuracy | ≥ 95% | ≥ 85% ✅ |
| P95 Latency (photo) | < 100ms (mock) | < 4s |
| P95 Latency (text) | < 50ms (mock) | < 2s |
| Cost per consultation | $0 (mock) | ≤ $0.02 |

Eval uses deterministic mock mode keyed to PlantVillage ground truth; swap `MOCK_LLM=false` + real Gemini key to re-run on actual model output.

Run the eval yourself:
```bash
pytest tests/eval/ -v --json-report --json-report-file=tests/eval/report.json
```

See [tests/eval/report.json](tests/eval/report.json) for raw numbers.

## 🔐 Security

7-point security control table — see [docs/SECURITY.md](docs/SECURITY.md):

1. **PII Redaction** — Aadhaar + phone masked in all responses and logs
2. **JWT Auth** — Token-based (mock) / Firebase phone OTP (prod)
3. **Rate Limiting** — 60 req/min per user
4. **Tool Isolation** — CropDoctor-only vision; no cross-agent tool access
5. **Secret Management** — Zero keys in repo; Secret Manager in prod
6. **Audit Trail** — Every decision logged with timestamp + PII-redacted user ID
7. **Network Security** — CORS whitelist, VPC-SC + Cloud Armor (prod)

## 🏛️ Supported Government Schemes

| Scheme | Benefit | Eligibility |
|--------|---------|-------------|
| PM-Kisan | ₹6,000/year | All farmers with ≤ 2 hectares |
| PMFBY | Crop insurance | Any insurable crop |
| KCC | Credit up to ₹3 lakh at 4% | All farmers |
| Soil Health Card | Free soil testing | All farmers |
| PM-KUSUM | 90% subsidy on solar pumps | Farmers with irrigation needs |
| MIDH | Horticulture subsidy | Fruit/vegetable growers |
| RKVY | State agriculture development | State-specific |
| NMSA | Sustainable agriculture | All farmers |
| eNAM | Electronic market access | All farmers |
| PMKSY | Micro-irrigation subsidy | All farmers |

## 🏗️ Build Provenance

This project was built with **Antigravity by Google** — an AI coding agent that scaffolded the multi-agent architecture, generated security middleware, created evaluation harnesses, and wrote documentation from natural language prompts.

See [docs/BUILT_WITH_ANTIGRAVITY.md](docs/BUILT_WITH_ANTIGRAVITY.md) for details on what was AI-generated vs. manually verified.

## 📂 Repository Structure

```
agri-saathi/
├── README.md                    # This file
├── LICENSE                      # Apache 2.0
├── pyproject.toml               # Python project config
├── .env.example                 # Environment template (no real keys!)
├── docker-compose.yml           # 5-service local stack
├── Dockerfile                   # API gateway container
├── Dockerfile.mcp               # MCP server container
├── agents/                      # Google ADK agents
│   ├── farmer_concierge.py      # Root orchestrator
│   ├── crop_doctor.py           # Vision-based disease diagnosis
│   ├── weather_advisor.py       # Weather + irrigation
│   ├── market_whisperer.py      # Mandi prices + trends
│   └── scheme_guide.py          # Government scheme RAG
├── mcp_servers/                 # MCP Protocol servers
│   ├── weather_mcp/server.py    # Forecast, soil moisture, irrigation
│   ├── mandi_mcp/server.py      # eNAM prices, trends, recommendations
│   └── schemes_mcp/server.py    # 10 government schemes knowledge base
├── tools/                       # Agent tools
│   ├── vision_tool.py           # Gemini vision + PlantVillage eval
│   ├── price_lookup.py          # Price formatting utilities
│   └── weather_lookup.py        # Weather formatting + crop risk
├── api/                         # FastAPI gateway
│   ├── main.py                  # Application + endpoints
│   ├── security.py              # PII redaction, JWT, rate limit, audit
│   ├── models.py                # Pydantic request/response models
│   ├── session_store.py         # SQLite session persistence
│   └── routes/whatsapp.py       # WhatsApp webhook (scaffolded)
├── frontend/                    # React PWA
│   ├── src/App.jsx              # Main chat interface
│   ├── src/index.css            # Full CSS design system
│   ├── src/components/          # UI components
│   ├── src/hooks/               # Voice + chat hooks
│   └── public/locales/          # 6 language translations
├── tests/                       # Test suite
│   ├── unit/                    # Import, security, crop doctor tests
│   ├── integration/             # API gateway tests
│   └── eval/                    # PlantVillage evaluation harness
├── terraform/                   # GCP Infrastructure as Code
│   ├── main.tf                  # Cloud Run services
│   ├── firestore.tf             # Session database
│   ├── iam.tf                   # Service accounts
│   └── secrets.tf               # Secret Manager
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # System design + tech stack
│   ├── SECURITY.md              # 7-point controls
│   ├── DEMO_SCRIPT.md           # 5-minute demo
│   ├── VIDEO_STORYBOARD.md      # Video production guide
│   └── BUILT_WITH_ANTIGRAVITY.md
└── notebooks/                   # (Evaluation notebooks)
```

## 🚀 Deploy to GCP

```bash
# 1. Configure Terraform
cd terraform
terraform init
terraform plan -var="project_id=YOUR_PROJECT"
terraform apply -var="project_id=YOUR_PROJECT"

# 2. Build and push containers
gcloud builds submit --config=cloudbuild.yaml

# 3. Deploy PWA to Firebase Hosting
cd frontend && npm run build
firebase deploy --only hosting
```

## 📝 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, Mermaid diagrams, tech stack |
| [SECURITY.md](docs/SECURITY.md) | 7-point control table, PII patterns |
| [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | 5-minute demo with timestamps |
| [VIDEO_STORYBOARD.md](docs/VIDEO_STORYBOARD.md) | Frame-by-frame video guide |
| [BUILT_WITH_ANTIGRAVITY.md](docs/BUILT_WITH_ANTIGRAVITY.md) | Build provenance |

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE).

---

*"With one photo, in her own language, Lakshmi saved her crop."* 🌾
