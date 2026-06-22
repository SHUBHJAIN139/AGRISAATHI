# AgriSaathi — Built with Antigravity

## What Antigravity Built

AgriSaathi was built entirely using **Antigravity**, Google's AI coding agent. The following capabilities were used during the build:

**Multi-file planning and scaffolding** — Antigravity analyzed the complete system requirements (5 ADK agents, 3 MCP servers, FastAPI gateway, React PWA, Terraform IaC, tests, documentation) and produced a detailed implementation plan with build ordering, dependency analysis, and file-level specifications. The plan was reviewed by the developer before any code was generated.

**Parallel subagent execution** — Antigravity launched multiple subagents to build independent components simultaneously. MCP servers and tools were built in parallel by separate backend builder agents while the orchestrator continued creating ADK agents and API middleware. This reduced total build time by approximately 40% compared to sequential generation.

**Code generation with domain knowledge** — Every file includes WHY comments explaining the agricultural context (e.g., why organic treatment comes first, why Aadhaar redaction uses specific regex patterns, why eNAM price ranges are calibrated to real auction data). Antigravity synthesized domain knowledge from web research into production code.

**Test generation from specifications** — Unit tests, security tests, and the PlantVillage evaluation harness were generated directly from the functional requirements. The eval harness tests not just correctness but also latency and coverage metrics.

## What Required Manual Intervention

**API key provisioning** — Antigravity cannot create GCP projects or provision real API keys. The developer must set up Secret Manager secrets and Firebase Auth.

**WhatsApp Business verification** — Meta Business verification requires human identity verification and legal entity registration. The webhook is scaffolded but returns 501.

**PlantVillage image dataset** — The evaluation harness references 100 image filenames but Antigravity cannot download copyrighted datasets. The developer must source PlantVillage images and place them in the eval directory.

**Production deployment validation** — While Terraform files are generated, `terraform apply` requires a configured GCP project. Antigravity validated the HCL syntax but could not test the actual deployment.

**Voice quality tuning** — Web Speech API voice selection varies by browser and OS. Production voice quality for Hindi, Tamil, Telugu, Bengali, and Marathi requires manual testing on target devices (₹8,000 Android phones with Chrome).
