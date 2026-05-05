import os
import json
import hashlib
import requests
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(str(PROJECT_ROOT / ".env"), override=True)

DATA_FILE = PROJECT_ROOT / "data" / "latest_threats.json"


def get_env(key):
    val = os.getenv(key)
    return val.strip().strip('\'"') if val else None


def get_embedding(text: str):
    cf_id = get_env("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env("CLOUDFLARE_API_KEY")
    if not cf_id or not cf_key:
        print("Cloudflare credentials not set")
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data.get("success"):
            return data["result"]["data"][0]
    except Exception as e:
        print(f"Embedding error: {e}")
    return None


def ingest():
    if not DATA_FILE.exists():
        print("No data/latest_threats.json found. Run CVE Pipeline first.")
        return

    pc_key = get_env("PINECONE_API_KEY")
    if not pc_key:
        print("PINECONE_API_KEY not set")
        return

    from pinecone import Pinecone
    pc = Pinecone(api_key=pc_key)
    index = pc.Index("evonet-memory")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cves = json.load(f)

    print(f"Loaded {len(cves)} CVEs from pipeline data")

    vectors_cve = []
    vectors_skill = []

    for cve_id, details in cves.items():
        summary = details.get("summary", "")
        cvss = details.get("cvss_score", 0)
        stage = details.get("stage", "")
        poc_url = details.get("poc_url", "")
        cwe_ids = details.get("cwe_ids", [])
        epss = details.get("epss_score", 0)
        attck = details.get("mitre_attack", [])

        text_for_embedding = f"{cve_id}: {summary}"
        if poc_url:
            text_for_embedding += f" PoC: {poc_url}"

        embedding = get_embedding(text_for_embedding)
        if not embedding:
            print(f"Skip {cve_id}: embedding failed")
            continue

        metadata = {
            "source": "github_pipeline",
            "status": "processed",
            "text": summary[:1000],
            "cvss_score": float(cvss) if cvss else 0.0,
            "stage": stage,
            "poc_url": poc_url,
            "cwe_ids": str(cwe_ids),
        }
        if epss:
            metadata["epss_score"] = float(epss)
        if attck:
            metadata["mitre_attack"] = str(attck)[:500]

        vectors_cve.append({
            "id": cve_id,
            "values": embedding,
            "metadata": metadata,
        })

        patch = details.get("patch_analysis", {})
        if patch.get("diff_code") and patch["diff_code"] not in ("To_be_generated", ""):
            patch_text = patch["diff_code"][:1000]
            patch_embedding = get_embedding(patch_text)
            if patch_embedding:
                patch_id = hashlib.md5(f"patch_{cve_id}".encode()).hexdigest()[:16]
                vectors_skill.append({
                    "id": f"skill_{patch_id}",
                    "values": patch_embedding,
                    "metadata": {
                        "source": cve_id,
                        "type": "defense_skill",
                        "text": patch_text,
                        "model_used": patch.get("status", "unknown"),
                    },
                })

    if vectors_cve:
        batch_size = 100
        for i in range(0, len(vectors_cve), batch_size):
            batch = vectors_cve[i : i + batch_size]
            index.upsert(vectors=batch, namespace="security_knowledge_clean")
        print(f"Upserted {len(vectors_cve)} CVEs to Pinecone")

    if vectors_skill:
        batch_size = 100
        for i in range(0, len(vectors_skill), batch_size):
            batch = vectors_skill[i : i + batch_size]
            index.upsert(vectors=batch, namespace="learned_skills")
        print(f"Upserted {len(vectors_skill)} patches to Pinecone")

    try:
        stats = index.describe_index_stats()
        ns = stats.get("namespaces", {})
        total_cve = ns.get("security_knowledge_clean", {}).get("vector_count", 0)
        total_skill = ns.get("learned_skills", {}).get("vector_count", 0)
        print(f"Pinecone totals — CVEs: {total_cve}, Skills: {total_skill}")
    except Exception:
        pass


if __name__ == "__main__":
    ingest()
