import os
import re
import time
import json
import threading
import subprocess
import shutil
import sys
import psutil
import requests
import httpx
from typing import List, Optional, Any
from functools import lru_cache
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from pinecone import Pinecone
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

_env_path = "/app/.env" if os.path.exists("/app/.env") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path, override=True)

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
_log_dir = "/app/logs" if os.path.isdir("/app/logs") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(_log_dir, exist_ok=True)
logger.add(os.path.join(_log_dir, "evonet.log"), rotation="10 MB", retention="7 days", level="DEBUG")

limiter = Limiter(key_func=get_remote_address)

REQUEST_COUNT = Counter('evonet_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('evonet_request_latency_seconds', 'Request latency', ['endpoint'])
AI_CALLS = Counter('evonet_ai_calls_total', 'AI provider calls', ['provider', 'status'])

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LOCAL_AI_BASE_URL = os.getenv("LOCAL_AI_BASE_URL", "http://host.docker.internal:11434/v1")
LOCAL_AI_MODEL = os.getenv("LOCAL_AI_MODEL", "qwen2.5-coder:14b")
LOCAL_AI_ENABLED = os.getenv("LOCAL_AI_ENABLED", "false").lower() == "true"
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

CF_MODEL = "@cf/qwen/qwen2.5-coder-32b-instruct"
GROQ_MODEL = "llama-3.3-70b-versatile"
NVIDIA_MODEL = "qwen/qwen2.5-coder-32b-instruct"


# ============================================================
# GUARDRAIL: Regex Blacklist
# ============================================================
def regex_blacklist_guardrail(code_to_check: str) -> bool:
    blacklisted_patterns = [
        r"os\.remove", r"shutil\.rmtree", r"subprocess\.run",
        r"subprocess\.Popen", r"DROP TABLE", r"DELETE FROM",
        r"rm -rf", r"eval\s*\(", r"exec\s*\(",
    ]
    for pattern in blacklisted_patterns:
        if re.search(pattern, code_to_check):
            error_msg = f"🚨 GUARDRAIL BLOCKED: dangerous pattern <code>{pattern}</code>"
            send_telegram_message(error_msg)
            raise Exception(f"Blocked dangerous pattern: {pattern}")
    return True


# ============================================================
# TELEGRAM
# ============================================================
def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=5)
    except Exception:
        pass


# ============================================================
# CACHE
# ============================================================
class SimpleCache:
    def __init__(self, max_size=1000):
        self._cache = {}
        self._access_times = {}
        self._max_size = max_size

    def get(self, key, default=None):
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return default

    def set(self, key, value, ttl=300):
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._access_times, key=lambda k: self._access_times[k])
            del self._cache[oldest_key]
            del self._access_times[oldest_key]
        self._cache[key] = value
        self._access_times[key] = time.time()

cache = SimpleCache()


# ============================================================
# PINECONE CONNECTION
# ============================================================
class PineconeConnectionPool:
    def __init__(self, api_key, index_name, pool_size=5):
        self.api_key = api_key
        self.index_name = index_name
        self.pool = []
        self.pool_size = pool_size
        self._initialize_pool()

    def _initialize_pool(self):
        for i in range(self.pool_size):
            try:
                pc = Pinecone(api_key=self.api_key)
                self.pool.append(pc.Index(self.index_name))
            except Exception as e:
                print(f"Pinecone connection {i} init error: {e}")

    def get_connection(self):
        if self.pool:
            return self.pool.pop()
        try:
            pc = Pinecone(api_key=self.api_key)
            return pc.Index(self.index_name)
        except Exception:
            return None

    def return_connection(self, conn):
        if len(self.pool) < self.pool_size and conn is not None:
            self.pool.append(conn)


pinecone_pool = PineconeConnectionPool(api_key=PINECONE_API_KEY, index_name="evonet-memory", pool_size=5)
pc = Pinecone(api_key=PINECONE_API_KEY)
memory_index = pc.Index("evonet-memory")
print("Pinecone connected")


# ============================================================
# EMBEDDING
# ============================================================
@lru_cache(maxsize=128)
def get_embedding_cached(text: str):
    return get_embedding(text)


def get_embedding(text: str):
    cache_key = f"embedding:{hash(text)}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_KEY}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data["success"]:
            result = data["result"]["data"][0]
            cache.set(cache_key, result)
            return result
        return None
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def retrieve_memory(query: str, namespace: str = "security_knowledge_clean"):
    try:
        query_vector = get_embedding_cached(query)
        if not query_vector:
            return ""

        global pinecone_pool
        index = pinecone_pool.get_connection()
        try:
            if index:
                results = index.query(namespace=namespace, vector=query_vector, top_k=3, include_metadata=True)
            else:
                results = memory_index.query(namespace=namespace, vector=query_vector, top_k=3, include_metadata=True)
        finally:
            if index:
                pinecone_pool.return_connection(index)

        results_dict: dict = dict(results)  # type: ignore[arg-type]

        if not results_dict.get('matches'):
            return ""

        context = ""
        for match in results_dict.get('matches', []):  # type: ignore[arg-type]
            metadata = match.get('metadata', {})  # type: ignore[union-attr]
            text_content = metadata.get('text', '') or metadata.get('raw_content', '')  # type: ignore[union-attr]
            score = match.get('score', 0)  # type: ignore[union-attr]
            context += f"MEMORY (Score {round(score * 100)}%): {text_content}\n---\n"
        return context.strip()
    except Exception as e:
        print(f"Pinecone retrieval error: {e}")
        return ""


# ============================================================
# AI PROVIDERS
# ============================================================
def call_cloudflare(prompt: str, system_prompt: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_MODEL}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_KEY}", "Content-Type": "application/json"}
    payload = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]}
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    return res.json()["result"]["response"]


def call_groq(prompt: str, system_prompt: str, temperature=0.6):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": temperature
    }
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    content = res.json()["choices"][0]["message"]["content"]
    return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()


def call_nvidia(prompt: str, system_prompt: str):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": NVIDIA_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": 0.2, "max_tokens": 4096
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=180)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "NVIDIA API timeout. Please try again."
    except Exception as e:
        return f"NVIDIA API error: {e}"


def call_local_ai(prompt: str, system_prompt: str):
    if not LOCAL_AI_ENABLED:
        raise Exception("Local AI not enabled")
    url = f"{LOCAL_AI_BASE_URL}/chat/completions"
    payload = {
        "model": LOCAL_AI_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    res = requests.post(url, json=payload, timeout=60)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


# ============================================================
# AI ROUTER
# ============================================================
def ai_router(user_message: str) -> str:
    if LOCAL_AI_ENABLED and len(user_message) < 50:
        return "LOCAL_PREFERRED"
    router_prompt = "Classify: TIER_1 (greeting), TIER_2 (logic), TIER_3 (code/security). Reply ONE word."
    try:
        decision = call_groq(user_message, router_prompt, temperature=0.0).upper()
        if "TIER_1" in decision:
            return "TIER_1"
        if "TIER_3" in decision:
            return "TIER_3"
        return "TIER_2"
    except Exception:
        return "TIER_2"


def process_ai_request(user_message: str) -> str:
    route = ai_router(user_message)
    memory_context = retrieve_memory(user_message)

    sensitive_keywords = [".env", "secret", "password", "api key"]
    if any(kw in user_message.lower() for kw in sensitive_keywords):
        return "Access denied: sensitive information request blocked."

    system_prompts = {
        "LOCAL_PREFERRED": "You are EvoNet Edge AI. Reply in Vietnamese, concise.",
        "TIER_1": "You are EvoNet Edge AI. Reply in Vietnamese, concise.",
        "TIER_2": f"You are EvoNet Core. Reply in Vietnamese. Memory:\n{memory_context}",
        "TIER_3": f"You are EvoNet Chief Engineer. Reply in Vietnamese. Memory:\n{memory_context}",
    }

    providers = {
        "LOCAL_PREFERRED": [("local", call_local_ai), ("cf", call_cloudflare)],
        "TIER_1": [("cf", call_cloudflare), ("local", call_local_ai)],
        "TIER_2": [("groq", call_groq), ("local", call_local_ai)],
        "TIER_3": [("nv", call_nvidia), ("groq", call_groq), ("local", call_local_ai)],
    }

    system_prompt = system_prompts[route]
    for name, func in providers[route]:
        try:
            reply = func(user_message, system_prompt)
            return f"EvoNet AI:\n\n{reply}"
        except Exception:
            continue
    return "All AI providers are currently unavailable."


# ============================================================
# TELEGRAM WORKER
# ============================================================
def execute_master_update(chat_id):
    send_telegram_message("🚨 <b>MASTER UPDATE TRIGGERED!</b>\nRunning full evolution cycle...")
    steps = [
        ("Step 0", "threat_intel_collector.py"), ("Step 1", "cve_refinery.py"),
        ("Step 2", "self_evolve.py"), ("Step 3", "evo_autofix.py"),
        ("Step 4", "advanced_static_analyzer.py"), ("Step 5", "attack_simulator.py"),
        ("Step 6", "threat_alert_system.py"), ("Step 7", "advanced_security.py"),
    ]
    for step_name, script in steps:
        send_telegram_message(f"⚙️ <b>{step_name}:</b> Running {script}...")
        try:
            subprocess.run(["python", f"scripts/{script}"], check=True, timeout=600)
        except Exception as e:
            send_telegram_message(f"⚠️ {step_name} error: {e}")

    subprocess.Popen(["python", "scripts/evo_architect_loop.py"])
    subprocess.Popen(["python", "scripts/auto_update_system.py"])
    send_telegram_message("✅ <b>MASTER UPDATE COMPLETE!</b>")


def telegram_worker():
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    print("Telegram listener started...")

    while True:
        try:
            res = requests.get(url, params={"offset": last_update_id + 1, "timeout": 30}, timeout=35)
            if res.status_code != 200:
                time.sleep(5)
                continue

            for update in res.json().get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()
                if not text or chat_id != TELEGRAM_CHAT_ID:
                    if chat_id != TELEGRAM_CHAT_ID and text:
                        print(f"Unknown ID {chat_id} attempted access")
                    continue

                if text == "/update":
                    threading.Thread(target=execute_master_update, args=(TELEGRAM_CHAT_ID,)).start()
                elif text == "/collect_threat":
                    send_telegram_message("Collecting threat intelligence...")
                    threading.Thread(target=lambda: subprocess.run(["python", "scripts/threat_intel_collector.py"])).start()
                elif text.startswith("/gat_cve"):
                    send_telegram_message("Collecting CVEs...")
                    subprocess.Popen(["python", "scripts/cve_refinery.py"])
                elif text.startswith("/gom_code"):
                    send_telegram_message("Harvesting codebase...")
                    subprocess.Popen(["python", "scripts/code_harvester.py"])
                elif text.startswith("/test_autofix"):
                    send_telegram_message("Running auto-fix...")
                    subprocess.Popen(["python", "scripts/evo_autofix.py"])
                elif text.startswith("/threat_alert"):
                    send_telegram_message("Checking threats...")
                    subprocess.Popen(["python", "scripts/threat_alert_system.py"])
                elif text.startswith("/simulate_attack"):
                    send_telegram_message("Simulating attacks...")
                    subprocess.Popen(["python", "scripts/attack_simulator.py"])
                elif text == "/duyet_tienhoa":
                    draft_path = "/app/main_draft.py"
                    target_path = "/app/main.py"
                    if os.path.exists(draft_path):
                        backup_dir = "/app/logs/backups"
                        os.makedirs(backup_dir, exist_ok=True)
                        backup_name = f"main_backup_{int(time.time())}.py"
                        shutil.copy(target_path, os.path.join(backup_dir, backup_name))
                        regex_blacklist_guardrail(open(draft_path).read())
                        shutil.copy(draft_path, target_path)
                        os.remove(draft_path)
                        send_telegram_message(f"🚀 <b>APPROVED!</b> Backup: {backup_name}. Restarting...")
                        sys.exit(1)
                    else:
                        send_telegram_message("No draft found")
                elif text == "/tu_choi":
                    draft = "/app/main_draft.py"
                    if os.path.exists(draft):
                        os.remove(draft)
                        send_telegram_message("🗑️ Draft rejected and deleted")
                    else:
                        send_telegram_message("No draft to reject")
                elif text.startswith("/auto_update"):
                    send_telegram_message("Starting auto-update...")
                    subprocess.Popen(["python", "scripts/auto_update_system.py"])
                else:
                    send_telegram_message("Processing...")
                    reply = process_ai_request(text)
                    send_telegram_message(reply)
        except Exception as e:
            print(f"Telegram worker error: {e}")
            time.sleep(5)


# ============================================================
# FEEDBACK ANALYSIS
# ============================================================
def analyze_user_feedback(message_text, ai_response):
    positive = ['tốt', 'hay', 'giỏi', 'chuẩn', 'đúng', '👍', 'like', 'tuyệt']
    negative = ['tệ', 'dở', 'sai', 'không đúng', '👎', 'dislike', 'kém', 'tồi']
    text_lower = message_text.lower()
    if any(kw in text_lower for kw in negative):
        return 'negative'
    if any(kw in text_lower for kw in positive):
        return 'positive'
    return 'neutral'


# ============================================================
# FASTAPI APP
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    send_telegram_message("🟢 <b>EVONET ONLINE</b>\nPinecone + AI Council connected!")
    threading.Thread(target=telegram_worker, daemon=True).start()
    app.state.start_time = time.time()
    yield
    send_telegram_message("🔴 <b>EVONET OFFLINE</b>")


app = FastAPI(title="EvoNet-Core API", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API AUTH MIDDLEWARE
# ============================================================
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not API_SECRET_KEY:
        return True
    if not credentials or credentials.credentials != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


class ChatCompletionRequest(BaseModel):
    model: str = "evonet-coder"
    messages: List[Any]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False


# ============================================================
# OPENAI-COMPATIBLE ENDPOINTS
# ============================================================
@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "evonet-architect", "object": "model", "owned_by": "evonet"},
            {"id": "evonet-coder", "object": "model", "owned_by": "evonet"},
            {"id": "evonet-speed", "object": "model", "owned_by": "evonet"},
        ]
    }


@app.post("/v1/chat/completions")
@limiter.limit("30/minute")
async def chat_completions(req: Request, _=Depends(verify_api_key)):
    REQUEST_COUNT.labels(method='POST', endpoint='/v1/chat/completions').inc()
    start_time = time.time()
    data = await req.json()
    model_requested = data.get("model", "evonet-coder").lower()
    messages = data.get("messages", [])
    is_stream = data.get("stream", False)

    user_query = ""
    target_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            target_idx = i
            content = messages[i].get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_query += part.get("text", "")
            else:
                user_query += str(content)
            break

    if target_idx != -1:
        try:
            memory_context = retrieve_memory(user_query)
            if memory_context:
                append_text = f"\n\n[EVO MEMORY]:\n{memory_context}"
                old_content = messages[target_idx]["content"]
                if isinstance(old_content, list):
                    messages[target_idx]["content"].append({"type": "text", "text": append_text})
                else:
                    messages[target_idx]["content"] += append_text
        except Exception:
            pass

    for msg in messages:
        if isinstance(msg.get("content"), list):
            flat = ""
            for part in msg["content"]:
                if isinstance(part, dict) and part.get("type") == "text":
                    flat += part.get("text", "")
            msg["content"] = flat

    NODE_NVIDIA = {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
        "model_name": "nvidia/qwen2.5-coder-32b-instruct", "label": "NVIDIA"
    }
    NODE_CF = {
        "url": f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {CLOUDFLARE_API_KEY}", "Content-Type": "application/json"},
        "model_name": "@cf/qwen/qwen2.5-coder-32b-instruct", "label": "Cloudflare"
    }
    NODE_GROQ = {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        "model_name": "qwen-2.5-32b", "label": "Groq"
    }
    NODE_LOCAL = {
        "url": f"{LOCAL_AI_BASE_URL}/chat/completions",
        "headers": {"Content-Type": "application/json"},
        "model_name": LOCAL_AI_MODEL, "label": "Local"
    }

    fallback_chain = []
    if "architect" in model_requested:
        fallback_chain = [NODE_NVIDIA, NODE_CF, NODE_GROQ]
    elif "speed" in model_requested:
        fallback_chain = [NODE_GROQ, NODE_CF, NODE_NVIDIA]
    else:
        fallback_chain = [NODE_CF, NODE_GROQ, NODE_NVIDIA]

    if LOCAL_AI_ENABLED:
        fallback_chain.insert(0, NODE_LOCAL)

    if is_stream:
        async def resilient_streamer():
            async with httpx.AsyncClient(timeout=30.0) as client:
                for node in fallback_chain:
                    data["model"] = node["model_name"]
                    try:
                        async with client.stream("POST", node["url"], headers=node["headers"], json=data) as r:
                            if r.status_code == 200:
                                async for line in r.aiter_lines():
                                    if line:
                                        yield f"{line}\n\n"
                                AI_CALLS.labels(provider=node['label'], status='success').inc()
                                return
                            else:
                                AI_CALLS.labels(provider=node['label'], status='error').inc()
                    except Exception:
                        AI_CALLS.labels(provider=node['label'], status='error').inc()
                        continue
            yield f'data: {json.dumps("All AI providers failed")}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(resilient_streamer(), media_type="text/event-stream")
    else:
        for node in fallback_chain:
            data["model"] = node["model_name"]
            try:
                res = requests.post(node["url"], headers=node["headers"], json=data, timeout=15)
                if res.status_code == 200:
                    return res.json()
            except Exception:
                continue
        return {"error": "All AI providers failed"}


# ============================================================
# MONITORING ENDPOINTS
# ============================================================
def get_system_stats():
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "timestamp": time.time()
    }


@app.get("/performance")
@app.get("/system-stats")
async def system_stats():
    return {
        "system": get_system_stats(),
        "uptime": time.time() - getattr(app.state, 'start_time', time.time()),
        "status": "healthy"
    }


@app.get("/pinecone-stats")
async def pinecone_stats():
    try:
        global pinecone_pool
        conn = pinecone_pool.get_connection()
        if conn:
            pinecone_pool.return_connection(conn)
            return {"status": "connected", "pool_size": len(pinecone_pool.pool)}
        return {"status": "not_initialized"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/graph-rag/search")
async def graph_rag_search(q: str, namespace: str = "security_knowledge_clean"):
    try:
        from graph_rag import get_graph_rag
        grag = get_graph_rag()
        result = grag.retrieve(q, namespace)
        return {"query": q, "context": result}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
