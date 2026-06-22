# AgriSaathi — Architecture

## System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        PWA["React PWA<br/>Voice I/O · 6 Languages<br/>Photo Capture"]
    end

    subgraph "API Gateway (FastAPI)"
        GW["FastAPI Gateway :8080"]
        AUTH["JWT Auth"]
        PII["PII Redaction<br/>(Aadhaar + Phone)"]
        RATE["Rate Limiter<br/>60 req/min"]
        AUDIT["Audit Logger"]
    end

    subgraph "Agent Layer (Google ADK)"
        FC["🌾 FarmerConcierge<br/>Root Orchestrator<br/>Intent + Language Detection"]
        CD["🔬 CropDoctor<br/>Gemini 2.0 Flash Vision<br/>Disease Diagnosis"]
        WA["🌤️ WeatherAdvisor<br/>Forecast + Irrigation"]
        MW["📊 MarketWhisperer<br/>Mandi Prices + Trends"]
        SG["🏛️ SchemeGuide<br/>Government Scheme RAG"]
    end

    subgraph "MCP Servers (FastMCP)"
        WS["weather_mcp :8081<br/>get_forecast<br/>get_soil_moisture<br/>irrigation_rule"]
        MS["mandi_mcp :8082<br/>get_mandi_price<br/>get_7day_trend<br/>recommend_action"]
        SS["schemes_mcp :8083<br/>search_schemes"]
    end

    subgraph "Storage"
        DB["SQLite / Firestore<br/>Session Memory"]
        LOG["Audit Log<br/>JSONL"]
    end

    PWA --> GW
    GW --> AUTH --> PII --> RATE --> FC
    FC -->|"photo intent"| CD
    FC -->|"weather intent"| WA
    FC -->|"price intent"| MW
    FC -->|"scheme intent"| SG
    WA --> WS
    MW --> MS
    SG --> SS
    FC --> DB
    GW --> AUDIT --> LOG
```

## Tech Stack

| Component | Technology | Why This Choice |
|-----------|-----------|-----------------|
| Agent Framework | Google ADK (LlmAgent) | Native Gemini integration, sub-agent delegation, MCP toolset support |
| LLM | Gemini 2.0 Flash | Multimodal (vision + text), low latency, cost-effective |
| MCP Servers | FastMCP (Python MCP SDK) | Standard tool protocol, stdio + SSE transports, ADK-native integration |
| API Gateway | FastAPI + Uvicorn | Async, Pydantic validation, middleware stack, OpenAPI docs |
| Frontend | React 18 + Vite PWA | Mobile-first, offline-capable, installable on ₹8,000 phones |
| Styling | Vanilla CSS + Custom Properties | No build dependency, mobile-optimized, Lighthouse ≥ 90 |
| i18n | i18next + react-i18next | 6 languages (EN, HI, TA, TE, BN, MR), lazy-loaded translations |
| Voice I/O | Web Speech API | Zero-dependency, Chrome-optimized, multilingual BCP-47 support |
| Session Store | SQLite (dev) / Firestore (prod) | Async, persistent, swappable backends |
| Auth | JWT (dev) / Firebase Phone OTP (prod) | Zero-password auth for farmers with feature phones |
| IaC | Terraform | Cloud Run, Firestore, Secret Manager, IAM — all declarative |
| Containerization | Docker + Docker Compose | 5-service local stack, production-identical builds |
| Testing | pytest + ADK AgentEvaluator | Unit, integration, trajectory-based eval harness |
| Security | PII Redaction + Tool Isolation | Defense-in-depth: regex middleware + Pydantic __repr__ + agent-level constraints |

## Data Flow: Photo Diagnosis

```mermaid
sequenceDiagram
    participant F as Farmer (Phone)
    participant API as FastAPI Gateway
    participant FC as FarmerConcierge
    participant CD as CropDoctor
    participant VT as Vision Tool

    F->>API: POST /diagnose {image_base64}
    API->>API: JWT Auth → PII Redact → Rate Limit
    API->>VT: analyze_crop_image(base64, filename)
    VT->>VT: Parse PlantVillage label OR call Gemini Vision
    VT-->>API: CropDiagnosis {disease, confidence, treatment}
    API->>API: Audit log entry
    API-->>F: JSON response + voice output
```

## Data Flow: Text Chat

```mermaid
sequenceDiagram
    participant F as Farmer
    participant API as FastAPI
    participant FC as FarmerConcierge
    participant SA as Sub-Agent
    participant MCP as MCP Server

    F->>API: POST /chat {message, language}
    API->>FC: Route to orchestrator
    FC->>FC: Detect intent + language
    FC->>SA: Delegate to specialist agent
    SA->>MCP: Call MCP tool (e.g., get_forecast)
    MCP-->>SA: Tool response (JSON)
    SA-->>FC: Formatted response in farmer's language
    FC-->>API: Response
    API-->>F: JSON + optional voice
```
