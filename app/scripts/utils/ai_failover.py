import os
import re
import requests
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)

NVIDIA_MODEL = "qwen/qwen2.5-coder-32b-instruct"
GROQ_MODEL = "llama-3.3-70b-versatile"
CF_MODEL = "@cf/qwen/qwen2.5-coder-32b-instruct"


def get_env_safe(key_name):
    val = os.getenv(key_name)
    if val:
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None


def send_telegram(msg):
    token = get_env_safe("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_safe("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception:
        pass


def ask_ai(prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> tuple:
    """4-tier AI failover. Returns (response_text, provider_name)."""
    nv_key = get_env_safe("NVIDIA_API_KEY")
    groq_key = get_env_safe("GROQ_API_KEY")
    cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env_safe("CLOUDFLARE_API_KEY")

    layers = [
        {
            "name": "NVIDIA",
            "url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"},
            "payload": {"model": NVIDIA_MODEL, "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature, "max_tokens": max_tokens},
            "parser": lambda r: r.json()["choices"][0]["message"]["content"],
            "timeout": 180
        },
        {
            "name": "Groq",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            "payload": {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature},
            "parser": lambda r: re.sub(r'<think>.*?</think>', '', r.json()["choices"][0]["message"]["content"], flags=re.DOTALL).strip(),
            "timeout": 60
        },
        {
            "name": "Local",
            "url": os.getenv("LOCAL_AI_BASE_URL", "http://host.docker.internal:11434/v1") + "/chat/completions",
            "headers": {"Content-Type": "application/json"},
            "payload": {"model": os.getenv("LOCAL_AI_MODEL", "qwen2.5-coder:14b"),
                        "messages": [{"role": "user", "content": prompt}]},
            "parser": lambda r: r.json()["choices"][0]["message"]["content"],
            "timeout": 120
        },
        {
            "name": "Cloudflare",
            "url": f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/{CF_MODEL}",
            "headers": {"Authorization": f"Bearer {cf_key}"},
            "payload": {"messages": [{"role": "user", "content": prompt}]},
            "parser": lambda r: r.json()["result"]["response"],
            "timeout": 60
        },
    ]

    local_enabled = os.getenv("LOCAL_AI_ENABLED", "false").lower() == "true"

    for layer in layers:
        if layer["name"] == "Local" and not local_enabled:
            continue
        if not layer["url"]:
            continue
        try:
            res = requests.post(layer["url"], headers=layer["headers"],
                                json=layer["payload"], timeout=layer["timeout"])
            if res.status_code == 200:
                result = layer["parser"](res)
                return result, layer["name"]
        except Exception:
            continue

    raise Exception("All 4 AI providers failed")


def get_embedding(text: str):
    cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env_safe("CLOUDFLARE_API_KEY")
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data.get("success"):
            return data["result"]["data"][0]
        return None
    except Exception:
        return None
