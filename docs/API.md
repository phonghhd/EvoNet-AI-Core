# EvoNet-Core API Reference

## Base URL
```
http://localhost:8080
```

## Authentication
Set `API_SECRET_KEY` in `.env` to enable Bearer token auth. If empty, all endpoints are open.

```
Authorization: Bearer your_secret_key
```

---

## Chat Completions (OpenAI-compatible)

### `POST /v1/chat/completions`

Rate limit: 30 requests/minute per IP.

**Request:**
```json
{
    "model": "evonet-coder",
    "messages": [{"role": "user", "content": "How to prevent SQL injection?"}],
    "temperature": 0.7,
    "stream": false
}
```

**Models:**
- `evonet-architect` — NVIDIA NIM first (best for planning/architecture)
- `evonet-coder` — Cloudflare first (best for code generation)
- `evonet-speed` — Groq first (fastest responses)

**Streaming:** Set `"stream": true` for SSE streaming via httpx async.

---

### `GET /v1/models`
Returns available model IDs.

---

## System Endpoints

### `GET /health`
```json
{"status": "ok"}
```

### `GET /system-stats` | `GET /performance`
```json
{
    "system": {
        "cpu_percent": 23.5,
        "memory_percent": 45.2,
        "disk_percent": 67.8,
        "memory_available_gb": 4.32
    },
    "uptime": 3600.5,
    "status": "healthy"
}
```

### `GET /pinecone-stats`
```json
{"status": "connected", "pool_size": 5}
```

### `GET /metrics`
Prometheus-compatible metrics endpoint. Returns:
- `evonet_requests_total` — Total API requests
- `evonet_request_latency_seconds` — Request latency histogram
- `evonet_ai_calls_total` — AI provider call counts by provider/status

---

## Graph RAG

### `GET /graph-rag/search?q=<query>&namespace=<namespace>`

Combined Neo4j + Pinecone retrieval. Returns vector matches enriched with knowledge graph context (related CVEs, defense skills, ATT&CK techniques).

---

## Dashboard API (port 8081)

### `GET /` — Dashboard UI
### `GET /api/stats` — Pinecone namespace counts
### `GET /api/system` — System metrics (CPU, RAM, Disk)
### `GET /api/activities` — Activity log from SQLite
### `GET /health` — Dashboard health check

---

## Advanced Security (CLI)

```bash
python app/scripts/advanced_security.py sbom [directory]     # Generate SBOM
python app/scripts/advanced_security.py secrets [directory]   # Scan for secrets
python app/scripts/advanced_security.py epss CVE-2024-1234   # Get EPSS score
python app/scripts/advanced_security.py attck CWE-89 CWE-79  # Get ATT&CK mappings
```
