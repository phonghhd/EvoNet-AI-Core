# Deployment Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- API keys: Pinecone, NVIDIA/Groq/Cloudflare, Telegram Bot

## Docker Deployment (Recommended)

```bash
git clone https://github.com/phonghhd/EvoNet-AI-Core.git
cd EvoNet-AI-Core

cp .env.example .env
nano .env  # Fill in your API keys

docker-compose up -d
```

Services:
- **API**: http://localhost:8080 (FastAPI + Telegram bot)
- **Dashboard**: http://localhost:8081 (Web UI)
- **Neo4j**: http://localhost:7474 (Browser) / bolt://localhost:7687
- **Metrics**: http://localhost:8080/metrics (Prometheus)

Health checks are configured on all services. Dashboard waits for API to be healthy.

## Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Terminal 1: API server
python app/main.py

# Terminal 2: Dashboard
python app/dashboard.py

# Terminal 3: Autonomous manager (24/7 scheduler)
python app/scripts/autonomous_manager.py
```

## CLI Installation

```bash
pip install -e .
evonet scan --path /path/to/your/code
evonet scan --tools bandit --output results.json
evonet version
```

## GitHub Actions (CVE Pipeline)

`.github/workflows/cve_crawler.yml` runs every 3 hours:
1. **Bot 1**: Fetches high-severity CVEs from CIRCL API (CVSS >= 7.0)
2. **Bot 2**: Searches GitHub for PoC repositories
3. **Bot 3**: AI-powered patch generation with 4-tier failover

Required GitHub Secrets:
- `PINECONE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_KEY`
- `GROQ_API_KEY`, `NVIDIA_API_KEY`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `PINECONE_API_KEY` | Yes | Pinecone vector DB key |
| `NVIDIA_API_KEY` | Yes | NVIDIA NIM API key |
| `GROQ_API_KEY` | Yes | Groq API key |
| `CLOUDFLARE_ACCOUNT_ID` | Yes | Cloudflare account |
| `CLOUDFLARE_API_KEY` | Yes | Cloudflare API key |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Yes | Telegram admin chat ID |
| `NEO4J_AUTH` | Yes | Neo4j credentials (user/password) |
| `LOCAL_AI_ENABLED` | No | Enable local Ollama (default: false) |
| `API_SECRET_KEY` | No | Bearer token for API auth |

## Monitoring

```bash
# Health check
curl http://localhost:8080/health

# System stats
curl http://localhost:8080/system-stats

# Prometheus metrics
curl http://localhost:8080/metrics

# Pinecone stats
curl http://localhost:8080/pinecone-stats

# Graph RAG search
curl "http://localhost:8080/graph-rag/search?q=SQL+injection"
```

## Logs

Logs are written to `/app/logs/evonet.log` with:
- Rotation: 10 MB per file
- Retention: 7 days
- Format: `YYYY-MM-DD HH:mm:ss | LEVEL | message`
