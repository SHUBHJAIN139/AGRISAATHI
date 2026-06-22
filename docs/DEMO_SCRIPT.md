# AgriSaathi — 5-Minute Demo Script

## Setup (before demo)

```bash
# Terminal 1: Start the backend
cd agri-saathi
cp .env.example .env
pip install -e ".[dev]"
uvicorn api.main:app --host 0.0.0.0 --port 8080

# Terminal 2: Start the frontend
cd agri-saathi/frontend
npm install
npm run dev
```

Open http://localhost:5173 in Chrome (best voice support).

---

## Demo Flow

### 0:00–0:30 — Welcome & Language Selection

1. Open the PWA → show the welcome screen with 🌾 icon and feature cards
2. **Point out:** "This is AgriSaathi — it runs on a ₹8,000 Android phone"
3. Click the **हिंदी** language button → UI text switches to Hindi
4. Show all 6 language buttons: English, हिंदी, தமிழ், తెలుగు, বাংলা, मराठी

> **Script:** "AgriSaathi supports 6 Indian languages. Let's start in Hindi."

### 0:30–1:15 — Crop Disease Diagnosis (CropDoctor)

1. Click the **📸 फसल रोग पहचान** feature card
2. System sends "मेरे टमाटर के पत्ते पीले हो रहे हैं" automatically
3. Show the response: disease diagnosis with organic treatment first
4. **Point out the agent badge:** "🔬 CropDoctor handled this"
5. Click 🔊 to hear the response read aloud in Hindi

> **Script:** "Lakshmi says her tomato leaves are turning yellow. CropDoctor diagnoses Late Blight in under 4 seconds. Notice: organic treatment comes first — neem oil, not chemicals."

### 1:15–1:45 — Photo Diagnosis

1. Click the **📷 camera button** in the input area
2. The photo modal opens — click "📷 फोटो लें / चुनें"
3. Select a sample leaf image (or take a photo if on mobile)
4. Click **🔬 विश्लेषण करें** (Analyze)
5. Show the **DiagnosisCard** appearing with glassmorphism styling:
   - Disease name, confidence %, severity badge
   - Organic treatment section highlighted

> **Script:** "Now let's use the camera. She takes a close-up of the leaf. The diagnosis card shows 95% confidence — Late Blight, medium severity. Treatment plan includes timing advice."

### 1:45–2:15 — Weather & Irrigation (WeatherAdvisor)

1. Type: "आज मौसम कैसा रहेगा? सिंचाई करूँ?"
2. Show the weather response with 7-day forecast
3. **Point out:** "🌤️ WeatherAdvisor" agent badge — different agent handled this
4. Highlight the irrigation advice: "आज सिंचाई करें, बुधवार से बारिश"

> **Script:** "Different question, different agent. WeatherAdvisor says irrigate today — rain is coming Wednesday. She saves water and doesn't overwater."

### 2:15–2:45 — Mandi Prices (MarketWhisperer)

1. Type: "टमाटर का आज मंडी भाव क्या है?"
2. Show price response with min/max/modal prices
3. **Point out:** "📊 MarketWhisperer" badge
4. Highlight: trend rising +12%, recommendation is "hold"
5. Show nearby mandi comparison: "Vashi ₹3,100 vs Azadpur ₹2,800"

> **Script:** "Tomatoes at Azadpur Mandi: ₹2,800 per quintal. But MarketWhisperer says hold — prices are rising 12%. And Vashi Mandi in Mumbai pays ₹300 more. That's ₹300 per quintal this farmer would have lost."

### 2:45–3:15 — Government Schemes (SchemeGuide)

1. Type: "मुझे सरकारी योजनाओं के बारे में बताओ"
2. Show PM-Kisan response with eligibility, documents, helpline
3. **Point out:** "🏛️ SchemeGuide" badge
4. Highlight: "₹6,000/year in 3 installments"
5. Show required documents list and helpline number

> **Script:** "She discovers PM-Kisan — ₹6,000 per year directly to her bank account. She didn't know she qualified. The documents she needs are listed: Aadhaar, bank passbook, land records."

### 3:15–3:45 — Voice Input Demo

1. Click the **🎤 microphone button** — it turns red (recording)
2. Speak in Hindi: "गेहूं का भाव बताओ"
3. Show the transcript appearing in the input field
4. Send → get MarketWhisperer response for wheat

> **Script:** "For low-literacy farmers, voice is essential. She presses the microphone, speaks in Hindi, and AgriSaathi understands."

### 3:45–4:15 — Language Switching (Tamil)

1. Click **தமிழ்** language button
2. Type or say: "நாளை மழை வருமா?" (Will it rain tomorrow?)
3. Show response in Tamil
4. Click 🔊 to hear Tamil speech output

> **Script:** "Same system, now in Tamil. A farmer in Tamil Nadu asks about tomorrow's rain. The response comes back in Tamil, and she can hear it spoken."

### 4:15–4:45 — Architecture Walkthrough

1. Open `docs/ARCHITECTURE.md` — show the Mermaid diagram
2. Point to: 5 agents, 3 MCP servers, FastAPI gateway
3. Show `api/security.py` — PII redaction code
4. Show audit log file — demonstrate that every decision is logged

> **Script:** "Behind the scenes: 5 ADK agents, 3 MCP servers for weather, market, and schemes data. Every interaction goes through PII redaction — Aadhaar numbers are never logged."

### 4:45–5:00 — Closing

1. Show the evaluation report: "top-3 accuracy ≥ 85%"
2. Show: `docker compose up` command
3. End with the PWA welcome screen

> **Script:** "AgriSaathi. Five AI agents. Six languages. One mission: help the farmer who needs it most. Built with Google ADK and Antigravity."
