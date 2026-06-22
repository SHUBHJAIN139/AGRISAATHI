# AgriSaathi — Security Controls

## 7-Point Security Control Table

| # | Control | Implementation | Location | Threat Mitigated |
|---|---------|---------------|----------|-----------------|
| 1 | **PII Redaction** | Regex-based scrubbing of Aadhaar (12-digit) and Indian phone numbers (+91XXXXXXXXXX) in all HTTP responses | `api/security.py` PIIRedactionMiddleware + `api/models.py` PIISafeModel.__repr__ | PII leakage in logs, error messages, third-party services |
| 2 | **Authentication** | JWT tokens (mock: HS256 shared secret; production: Firebase phone OTP with public key validation) | `api/security.py` JWTAuthMiddleware | Unauthorized API access |
| 3 | **Rate Limiting** | Per-user sliding window: 60 requests/minute. Identified by JWT user_id or IP fallback | `api/security.py` RateLimitMiddleware | DoS, abuse, cost explosion |
| 4 | **Tool Isolation** | CropDoctor is the ONLY agent with vision tool. WeatherAdvisor, MarketWhisperer, SchemeGuide have NO camera access | `agents/*.py` — tools parameter in Agent() constructor | Privilege escalation, data leakage between agents |
| 5 | **Secret Management** | `.env.example` has placeholders only. Production secrets in GCP Secret Manager. Zero keys in repo | `.env.example`, `terraform/secrets.tf` | Key exposure in source control |
| 6 | **Audit Trail** | Every agent delegation, tool call, and response logged as JSONL with timestamp, user_id (PII-redacted), session_id, action | `api/security.py` AuditLogger | Non-repudiation, debugging, compliance |
| 7 | **Network Security** | CORS whitelist, VPC-SC perimeter + Cloud Armor WAF (production). Docker network isolation (dev) | `api/main.py` CORSMiddleware, `terraform/main.tf` | CSRF, DDoS, unauthorized network access |

## PII Redaction Patterns

| Data Type | Pattern | Redacted Form | Example |
|-----------|---------|---------------|---------|
| Aadhaar (spaces) | `1234 5678 9012` | `XXXX-XXXX-9012` | "Mera Aadhaar 1234 5678 9012 hai" → "Mera Aadhaar XXXX-XXXX-9012 hai" |
| Aadhaar (hyphens) | `1234-5678-9012` | `XXXX-XXXX-9012` | Same masking, last 4 digits preserved |
| Aadhaar (no sep) | `123456789012` | `XXXX-XXXX-9012` | Contiguous 12-digit number |
| Phone (+91) | `+919876543210` | `+91-XXXXX-XX210` | Prefix preserved, middle digits masked |
| Phone (91) | `919876543210` | `91-XXXXX-XX210` | Same pattern without + |
| Phone (0) | `09876543210` | `0-XXXXX-XX210` | Local dialing format |

## Agent Tool Isolation Matrix

| Agent | Vision Tool | Weather MCP | Mandi MCP | Schemes MCP |
|-------|:-----------:|:-----------:|:---------:|:-----------:|
| FarmerConcierge | ❌ | ❌ | ❌ | ❌ |
| CropDoctor | ✅ | ❌ | ❌ | ❌ |
| WeatherAdvisor | ❌ | ✅ | ❌ | ❌ |
| MarketWhisperer | ❌ | ❌ | ✅ | ❌ |
| SchemeGuide | ❌ | ❌ | ❌ | ✅ |

> FarmerConcierge has NO tools — it delegates only. This prevents prompt injection from bypassing tool isolation.

## SchemeGuide PII Safety

SchemeGuide handles eligibility data (land size, income, caste category) but:
- **NEVER** asks for Aadhaar number
- **NEVER** asks for bank account details
- **NEVER** stores passwords
- If a farmer shares their Aadhaar, the agent instructs them NOT to share it online
- PII redaction middleware strips any accidentally shared Aadhaar before logging
