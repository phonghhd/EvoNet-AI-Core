<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:000000,100:002200&height=200&section=header&text=EVONET%20CORE&fontSize=60&fontColor=00ff00&desc=Autonomous%20AI%20Security%20Agent&descSize=20&descAlignY=70" alt="EvoNet Banner">

  # EvoNet-Core: Autonomous AI Security Agent

  **Self-Learning Security System with Multi-Tier LLM Routing, Graph RAG, RL Defense, and MITRE ATT&CK Integration**

  [![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
  [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
</div>

---

EvoNet-Core is an autonomous AI security agent that continuously harvests CVE data, analyzes vulnerabilities, and generates defensive code. It combines **4-tier AI failover**, **Knowledge Graph + Vector RAG**, **Reinforcement Learning defense optimization**, **MITRE ATT&CK mapping**, **EPSS scoring**, and **human-in-the-loop approval** into a unified security platform.

## Features

### Multi-Tier AI Routing (4-Layer Failover)
**NVIDIA NIM → Groq → Cloudflare AI → Local Ollama** — zero downtime during rate limits.

### Graph RAG (Knowledge Graph + Vector Retrieval)
**Pinecone** vector DB for CVE/defense embeddings + **Neo4j** knowledge graph for structured threat relationships (CVE → CWE → Software → Defense Skills → ATT&CK Techniques). Combined retrieval eliminates hallucinations.

### MITRE ATT&CK Integration
Automatic mapping of CVEs to ATT&CK techniques via CWE analysis. Stored in Neo4j for attack path analysis.

### EPSS Scoring
FIRST EPSS API integration for exploit prediction scoring. Prioritizes CVEs by likelihood of exploitation, not just CVSS.

### Reinforcement Learning Defense Agent
PPO-based RL agent trained on CVE features to suggest optimal defense strategies (10 strategies: input validation, output encoding, WAF, etc.). Integrated into the self-evolution pipeline.

### Federated Learning
Local model fine-tuning from user feedback with FedAvg aggregation. Privacy-preserving continuous improvement.

### Proactive Defense
- **Regex Guardrail**: Blocks destructive patterns (`rm -rf`, `DROP TABLE`, `eval`, `exec`)
- **Human-in-the-Loop**: Draft patches require Telegram approval
- **Attack Simulator**: Tests patch effectiveness against SQL injection, XSS, command injection
- **Secrets Scanner**: Detects API keys, passwords, tokens in codebase
- **SBOM Generator**: CycloneDX-compatible software bill of materials

### Production Infrastructure
- **Structured Logging**: Loguru with rotation and retention
- **Prometheus Metrics**: Request counts, latency, AI call stats
- **Rate Limiting**: Slowapi per-endpoint rate limiting
- **Health Checks**: Docker health checks on all services
- **API Authentication**: Bearer token auth for API endpoints

### CI/CD & Interactivity
- CLI tooling with Typer & Rich (real SAST scanning)
- Telegram bot for 24/7 monitoring and remote control
- GitHub Actions pipeline for automated CVE harvesting + patching

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/phonghhd/EvoNet-AI-Core.git
cd EvoNet-AI-Core

cp .env.example .env
# Edit .env with your API keys

docker-compose up -d
```

- API: http://localhost:8080
- Dashboard: http://localhost:8081
- Neo4j Browser: http://localhost:7474
- Prometheus Metrics: http://localhost:8080/metrics

### Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python app/main.py          # API server
python app/dashboard.py     # Dashboard
python app/scripts/autonomous_manager.py  # 24/7 scheduler
```

### CLI

```bash
pip install -e .
evonet scan --path /path/to/your/code
evonet scan --tools bandit
evonet scan --output results.json
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/update` | Full evolution cycle (CVE → analysis → ATT&CK → EPSS → patching) |
| `/gat_cve` | Harvest new CVEs from NVD |
| `/test_autofix` | Scan code and propose patches |
| `/duyet_tienhoa` | Approve and apply draft patch |
| `/tu_choi` | Reject draft patch |
| `/collect_threat` | Collect threat intelligence |
| `/threat_alert` | Check for new threats |
| `/simulate_attack` | Test patch effectiveness |
| `/auto_update` | Start 24/7 autonomous scheduler |

## Architecture

```
Telegram / CLI → FastAPI Backend → AI Router (4-Tier Fallback)
                                    ├── NVIDIA NIM
                                    ├── Groq
                                    ├── Cloudflare AI
                                    └── Local Ollama
                → Graph RAG (Pinecone + Neo4j)
                → MITRE ATT&CK Mapping
                → EPSS Scoring
                → RL Defense Agent (PPO)
                → Guardrail System → Auto-Patching Engine
                → Prometheus Metrics + Loguru Logging
```

## Project Structure

```
evonet-core/
├── app/
│   ├── main.py                 # FastAPI + Telegram + httpx streaming
│   ├── dashboard.py            # Web dashboard (port 8081)
│   ├── kg_manager.py           # Neo4j Knowledge Graph
│   ├── advanced_rag.py         # Vector RAG retrieval
│   ├── graph_rag.py            # Graph RAG (Neo4j + Pinecone)
│   ├── cli.py                  # CLI tool (Typer + real SAST)
│   ├── setup.py                # Package setup
│   ├── scripts/
│   │   ├── autonomous_manager.py   # 24/7 APScheduler (15 jobs)
│   │   ├── cve_refinery.py         # NVD CVE ingestion + KG
│   │   ├── self_evolve.py          # Self-learning + RL integration
│   │   ├── self_qa.py              # Synthetic QA generation
│   │   ├── evo_autofix.py          # Auto-patching + GitHub PR
│   │   ├── evo_architect_loop.py   # Code optimization
│   │   ├── analyze_patch.py        # AI-powered patch generation
│   │   ├── advanced_security.py    # ATT&CK + EPSS + SBOM + Secrets
│   │   ├── threat_intel_collector.py
│   │   ├── threat_alert_system.py
│   │   ├── attack_simulator.py
│   │   ├── advanced_static_analyzer.py
│   │   ├── code_harvester.py
│   │   ├── auto_update_system.py
│   │   ├── multi_language_support.py
│   │   └── brain/                  # Local AI modules
│   ├── federated_learning/     # FL training (FedAvg)
│   ├── rl_environment/         # RL defense agent (PPO + Gymnasium)
│   └── templates/              # Dashboard HTML
├── docs/                       # Documentation
├── tests/                      # Test suite
├── .github/workflows/          # CI/CD pipeline
├── docker-compose.yml
├── Dockerfile.optimized
└── requirements.txt
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## Testing

```bash
pip install pytest
pytest tests/ -v
```

## Disclaimer

EvoNet-Core is developed for **educational, research, and defensive purposes only**. Always use version control and review AI-generated patches before deploying to production.

## License

[Apache License 2.0](LICENSE.md)
