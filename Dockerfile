# =============================================================================
# AgriSaathi — Main Dockerfile (API Gateway + Agents)
# =============================================================================
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY agents/ ./agents/
COPY mcp_servers/ ./mcp_servers/
COPY tools/ ./tools/
COPY api/ ./api/

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Create data directory for SQLite + audit logs
RUN mkdir -p /app/data

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the API gateway
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
