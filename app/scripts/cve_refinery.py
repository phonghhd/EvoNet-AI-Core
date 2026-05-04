import os
import requests
from pinecone.pinecone import Pinecone
import re
from dotenv import load_dotenv
load_dotenv("/app/.env", override=True)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def get_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index("evonet-memory")


memory_index = get_pinecone_index()


def get_embedding(text: str):
    cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    cf_key = os.getenv("CLOUDFLARE_API_KEY")
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data.get("success"):
            return data["result"]["data"][0]
        return None
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None


def ai_sanitize_data(raw_desc):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Phân tích lỗ hổng này, loại bỏ ký tự nguy hiểm, tóm tắt bằng tiếng Việt chuyên sâu: {raw_desc}"
    payload = {
        "model": "qwen/qwen3-32b",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        content = res.json()["choices"][0]["message"]["content"]
        return re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
    except Exception:
        return raw_desc


def extract_cwe_ids(description):
    cwe_pattern = r'CWE-\d{1,4}'
    matches = re.findall(cwe_pattern, description, re.IGNORECASE)
    return list(set(matches))


def process_cve():
    print("Fetching latest CVEs from NVD...")
    nvd_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=3"
    new_cve_count = 0
    MAX_CVE_PER_RUN = 10

    try:
        raw_data = requests.get(nvd_url, timeout=30).json()
    except Exception as e:
        print(f"Error fetching from NVD: {e}")
        return

    for item in raw_data.get("vulnerabilities", []):
        if new_cve_count >= MAX_CVE_PER_RUN:
            break

        cve_id = item["cve"]["id"]
        raw_desc = item["cve"]["descriptions"][0]["value"]

        # AI sanitize
        print(f"Sanitizing {cve_id}...")
        clean_desc = ai_sanitize_data(raw_desc)

        # Extract metadata
        cvss_score = None
        cwe_ids = []
        published_date = ""
        try:
            cve_data = item["cve"]
            published_date = cve_data.get("published", "")
            metrics = cve_data.get("metrics", {})
            if metrics:
                for key in ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
                    if key in metrics and metrics[key]:
                        cvss_score = metrics[key][0].get('cvssData', {}).get('baseScore')
                        break
            weaknesses = cve_data.get("weaknesses", [])
            for weakness in weaknesses:
                for desc in weakness.get('description', []):
                    if desc.get('lang') == 'en' and desc.get('value', '').startswith('CWE-'):
                        cwe_ids.append(desc['value'])
            if not cwe_ids:
                cwe_ids = extract_cwe_ids(raw_desc)
        except Exception as e:
            print(f"Warning: metadata extraction error for {cve_id}: {e}")

        # Store in Knowledge Graph
        try:
            from kg_manager import get_kg_instance
            kg = get_kg_instance()
            if kg.driver is not None:
                kg.add_cve_node(
                    cve_id=cve_id, description=clean_desc,
                    cvss_score=cvss_score, cwe_ids=cwe_ids,
                    affected_software=[], exploit_maturity='unknown',
                    published_date=published_date
                )
                print(f"Added {cve_id} to Knowledge Graph")
        except Exception as e:
            print(f"Warning: KG error for {cve_id}: {e}")

        # Store in Pinecone
        vector_data = get_embedding(clean_desc)
        if vector_data:
            memory_index.upsert(
                vectors=[{
                    "id": cve_id,
                    "values": vector_data,
                    "metadata": {
                        "source": "NVD",
                        "status": "sanitized",
                        "text": clean_desc,
                        "cvss_score": cvss_score or 0.0,
                        "cwe_ids": str(cwe_ids),
                        "published_date": published_date
                    }
                }],
                namespace="security_knowledge_clean"
            )
            print(f"Stored {cve_id} in Pinecone")
        else:
            print(f"Warning: embedding failed for {cve_id}")

        new_cve_count += 1

    print(f"Done. Processed {new_cve_count} CVEs.")


if __name__ == "__main__":
    process_cve()
