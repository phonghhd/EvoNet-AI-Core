import json
import os
import sys
import re
import requests
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)

DATA_FILE = "data/latest_threats.json"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


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


def ask_ai_with_failover(prompt):
    """4-tier AI failover to generate patch code"""
    nv_key = get_env_safe("NVIDIA_API_KEY")
    groq_key = get_env_safe("GROQ_API_KEY")
    cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env_safe("CLOUDFLARE_API_KEY")

    layers = [
        {
            "name": "NVIDIA",
            "url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"},
            "payload": {"model": "qwen/qwen2.5-coder-32b-instruct", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 4096},
            "parser": lambda r: r.json()["choices"][0]["message"]["content"]
        },
        {
            "name": "Groq",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            "payload": {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            "parser": lambda r: r.json()["choices"][0]["message"]["content"]
        },
        {
            "name": "Cloudflare",
            "url": f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/qwen/qwen2.5-coder-32b-instruct",
            "headers": {"Authorization": f"Bearer {cf_key}"},
            "payload": {"messages": [{"role": "user", "content": prompt}]},
            "parser": lambda r: r.json()["result"]["response"]
        },
    ]

    for layer in layers:
        try:
            res = requests.post(layer["url"], headers=layer["headers"], json=layer["payload"], timeout=180)
            if res.status_code == 200:
                return layer["parser"](res), layer["name"]
        except Exception:
            continue

    raise Exception("All AI providers failed")


def generate_patch_for_cve(cve_id, details):
    """Use AI to generate a real security patch for a CVE"""
    summary = details.get("summary", "No summary available")
    poc_url = details.get("poc_url", "No PoC")
    cwe_ids = details.get("cwe_ids", [])

    prompt = f"""You are a senior security engineer. Analyze this CVE and generate a concrete code patch.

CVE ID: {cve_id}
Summary: {summary}
PoC URL: {poc_url}
CWE IDs: {', '.join(cwe_ids) if cwe_ids else 'Unknown'}

Generate:
1. A brief explanation of the vulnerability mechanism (2-3 sentences)
2. A concrete Python code patch that mitigates this vulnerability
3. Step-by-step mitigation instructions

Format your response as:
VULNERABILITY: <explanation>
PATCH:
```python
<actual patch code>
```
MITIGATION:
- <step 1>
- <step 2>
- <step 3>"""

    response, model = ask_ai_with_failover(prompt)
    return response, model


def parse_ai_response(response):
    """Parse AI response into structured patch data"""
    result = {
        "vulnerability": "",
        "patch_code": "",
        "mitigation_steps": []
    }

    vuln_match = re.search(r'VULNERABILITY:\s*(.*?)(?=PATCH:|$)', response, re.DOTALL)
    if vuln_match:
        result["vulnerability"] = vuln_match.group(1).strip()

    patch_match = re.search(r'```python\s*(.*?)```', response, re.DOTALL)
    if patch_match:
        result["patch_code"] = patch_match.group(1).strip()

    mit_match = re.search(r'MITIGATION:\s*(.*?)$', response, re.DOTALL)
    if mit_match:
        steps = re.findall(r'-\s*(.+)', mit_match.group(1))
        result["mitigation_steps"] = [s.strip() for s in steps]

    if not result["patch_code"]:
        result["patch_code"] = response[:2000]

    return result


def analyze_patch():
    if not os.path.exists(DATA_FILE):
        print("No data file found")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cves = json.load(f)

    updated = False
    processed = 0

    for cve_id, details in cves.items():
        if details.get("stage") in ["2_PoC_Found", "2_No_PoC"]:
            print(f"Generating patch for {cve_id}...")

            try:
                ai_response, model = generate_patch_for_cve(cve_id, details)
                parsed = parse_ai_response(ai_response)

                details["patch_analysis"] = {
                    "status": f"Patched_by_{model}",
                    "diff_code": parsed["patch_code"],
                    "vulnerability_explanation": parsed["vulnerability"],
                    "mitigation_steps": parsed["mitigation_steps"]
                }
                details["stage"] = "3_Ready_for_Fine_Tuning"
                updated = True
                processed += 1
                print(f"Patch generated for {cve_id} using {model}")

            except Exception as e:
                print(f"Failed to generate patch for {cve_id}: {e}")
                details["patch_analysis"] = {
                    "status": "generation_failed",
                    "error": str(e)
                }
                details["stage"] = "3_Patch_Failed"

    if updated:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cves, f, indent=4, ensure_ascii=False)
        send_telegram(f"🛡️ <b>PATCH ANALYSIS:</b>\nGenerated {processed} patches from CVE data")
        print(f"Done. Generated {processed} patches.")
    else:
        print("No CVEs ready for patching")


if __name__ == "__main__":
    analyze_patch()
