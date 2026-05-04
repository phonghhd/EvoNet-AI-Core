# EvoNet-Core Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      EvoNet-Core Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │ Telegram  │───▶│  FastAPI     │───▶│  AI Router   │           │
│  │ CLI       │    │  Backend     │    │  (4-Tier)    │           │
│  └──────────┘    │  :8080       │    └──────┬───────┘           │
│                  └──────┬───────┘           │                    │
│                         │          ┌───────┼───────┬──────┐     │
│                         │          │       │       │      │     │
│                         │       NVIDIA   Groq   CF AI  Local   │
│                         │                                         │
│  ┌──────────────────────┼──────────────────────────────────────┐ │
│  │              Knowledge Layer                                │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ Pinecone │  │  Neo4j   │  │ Graph    │  │ SQLite   │   │ │
│  │  │ Vector DB│  │  KG      │  │ RAG      │  │ Dashboard│   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Intelligence Layer                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ MITRE    │  │  EPSS    │  │ RL Agent │  │ FL System│   │ │
│  │  │ ATT&CK   │  │  Scoring │  │ (PPO)    │  │ (FedAvg) │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Defense Layer                                   │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ Guardrail│  │  Auto    │  │ Attack   │  │ Secrets  │   │ │
│  │  │ (Regex)  │  │  Patch   │  │ Simulator│  │ Scanner  │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Observability Layer                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │ │
│  │  │ Loguru   │  │Prometheus│  │ Rate     │                  │ │
│  │  │ Logging  │  │ Metrics  │  │ Limiting │                  │ │
│  │  └──────────┘  └──────────┘  └──────────┘                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. API Layer (`app/main.py`)
- OpenAI-compatible `/v1/chat/completions` with async httpx streaming
- 4-tier AI failover: NVIDIA NIM → Groq → Cloudflare AI → Local Ollama
- Graph RAG: combines Pinecone vector search + Neo4j graph traversal
- Telegram bot with HITL approval flow
- Regex guardrail, rate limiting, API key auth
- Prometheus metrics at `/metrics`

### 2. Knowledge Layer
- **Pinecone**: Namespaces for CVEs, threat intel, defense skills, codebase
- **Neo4j**: CVE → CWE → Software → DefenseSkill → ATTCKTechnique
- **Graph RAG**: Merges vector similarity with graph relationships

### 3. Intelligence Layer
- **MITRE ATT&CK**: CWE-to-technique mapping stored in Neo4j
- **EPSS**: FIRST API for exploit prediction scoring
- **RL Agent**: PPO model suggests optimal defense strategy per CVE
- **FL System**: FedAvg aggregation of client model updates

### 4. Defense Layer
- **Regex Guardrail**: Blocks dangerous patterns before execution
- **Auto-Patch**: AI-generated patches with HITL approval
- **Attack Simulator**: Tests patches against injection payloads
- **Secrets Scanner**: Detects API keys, tokens, passwords

### 5. Observability Layer
- **Loguru**: Structured logging with rotation
- **Prometheus**: Request counts, latency, AI call metrics
- **Rate Limiting**: Slowapi per-endpoint limits

## Data Flow

### CVE Pipeline
```
NVD/CIRCL → cve_refinery.py → AI Sanitize → Pinecone + Neo4j
    → analyze_patch.py → AI Generate Patch → Telegram HITL
    → advanced_security.py → EPSS + ATT&CK Enrichment
```

### Self-Evolution
```
Pinecone CVE → self_evolve.py → AI Generate Defense
    → RL Agent Suggest Strategy → Store in learned_skills
    → Knowledge Graph Link (MITIGATES)
```

### 24/7 Autonomous Loop (APScheduler)
```
30min: Health Check + System Monitor
1h:   CVE Scanning
2h:   System Watchdog
3h:   Code Harvesting
4h:   Threat Intel Collection
5h:   Continuous Learning
6h:   Self-Evolution + Security Assessment
8h:   Advanced Static Analysis
12h:  Comprehensive Update
1d:   Federated Learning + Incident Response
3d:   Bug Bounty Hunting
```

## Telegram Commands

| Command | Script | Description |
|---------|--------|-------------|
| `/update` | All pipeline scripts | Full evolution cycle |
| `/gat_cve` | cve_refinery.py | Harvest CVEs from NVD |
| `/test_autofix` | evo_autofix.py | Auto-patch with AI |
| `/duyet_tienhoa` | main.py | Approve draft patch |
| `/tu_choi` | main.py | Reject draft patch |
| `/collect_threat` | threat_intel_collector.py | Collect threat intel |
| `/threat_alert` | threat_alert_system.py | Check new threats |
| `/simulate_attack` | attack_simulator.py | Test patches |
| `/auto_update` | auto_update_system.py | Start scheduler |
| `/gom_code` | code_harvester.py | Harvest workspace code |
