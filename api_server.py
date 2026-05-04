import os
import sys
import re
import time
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"

_env = PROJECT_ROOT / ".env"
load_dotenv(str(_env), override=True)

sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "scripts" / "utils"))

from main import (  # type: ignore[import-untyped]  # noqa: E402
    app,
    send_telegram_message,
    retrieve_memory,
    get_embedding,
    regex_blacklist_guardrail,
    memory_index,
)

from fastapi import HTTPException, Request  # noqa: E402
from github import Github  # noqa: E402

GITHUB_BOT_TOKEN = os.getenv("GITHUB_BOT_TOKEN") or os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "phonghhd/vietnamese-ai")
DASHBOARD_DB = APP_DIR / "dashboard.db"


class ScanPayload(BaseModel):
    repo: str
    branch: str
    commit_sha: str
    code_diff: str
    file_path: str


def log_activity(action: str, status: str, status_class: str = "success"):
    try:
        conn = sqlite3.connect(str(DASHBOARD_DB))
        c = conn.cursor()
        c.execute(
            "INSERT INTO activities (timestamp, action, status, status_class) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, status, status_class),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def query_kg_context(cwe_patterns: list) -> str:
    try:
        from kg_manager import get_kg_instance  # type: ignore[import-untyped]

        kg = get_kg_instance()
        if kg.driver is None:
            return ""
        parts = []
        for cwe in cwe_patterns:
            with kg.driver.session() as session:
                result = session.run(
                    """
                    MATCH (w:CWE {id: $cwe})<-[:HAS_WEAKNESS]-(c:CVE)
                    OPTIONAL MATCH (d:DefenseSkill)-[:MITIGATES]->(c)
                    RETURN c.id as cve, c.cvss_score as cvss, collect(d.description)[..2] as defenses
                    LIMIT 3
                    """,
                    cwe=cwe,
                )
                for rec in result:
                    defs = [d[:100] for d in rec["defenses"] if d]
                    parts.append(f"{rec['cve']} (CVSS:{rec['cvss']}): {', '.join(defs) or 'no defense'}")
        return "\n".join(parts)
    except Exception:
        return ""


def post_github_comment(repo_name: str, commit_sha: str, body: str):
    if not GITHUB_BOT_TOKEN:
        return
    full_repo = f"phonghhd/{repo_name}" if "/" not in repo_name else repo_name
    url = f"https://api.github.com/repos/{full_repo}/commits/{commit_sha}/comments"
    headers = {"Authorization": f"token {GITHUB_BOT_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        requests.post(url, headers=headers, json={"body": body}, timeout=10)
    except Exception:
        pass


def create_auto_pr(repo_name: str, commit_sha: str, file_path: str, patched_code: str):
    if not GITHUB_BOT_TOKEN:
        return None
    try:
        full_repo = f"phonghhd/{repo_name}" if "/" not in repo_name else repo_name
        g = Github(GITHUB_BOT_TOKEN)
        repo = g.get_repo(full_repo)
        branch = f"evonet-patch-{commit_sha[:7]}"
        main = repo.get_branch(repo.default_branch)
        repo.create_git_ref(ref=f"refs/heads/{branch}", sha=main.commit.sha)
        file_sha = ""
        content_data = repo.get_contents(file_path, ref=repo.default_branch)
        if isinstance(content_data, list):
            file_sha = content_data[0].sha
        else:
            file_sha = content_data.sha
        repo.update_file(
            path=file_path,
            message="EvoNet Auto-Patch: Security fix",
            content=patched_code,
            sha=file_sha,
            branch=branch,
        )
        pr = repo.create_pull(
            title=f"[EvoNet] Security fix for {file_path}",
            body=f"Auto-generated security patch for commit {commit_sha[:7]}.",
            head=branch,
            base=repo.default_branch,
        )
        return pr.html_url
    except Exception as e:
        print(f"Auto-PR error: {e}")
        return None


@app.post("/api/v1/scan")
async def scan_code(payload: ScanPayload):
    print(f"[SCAN] {payload.repo} | {payload.branch} | {payload.file_path}")
    ignored_extensions = (".json", ".csv", ".md", ".txt")
    start = time.time()

    guardrail_hits = []
    patterns = [
        (r"os\.remove", "os.remove"),
        (r"shutil\.rmtree", "shutil.rmtree"),
        (r"eval\s*\(", "eval()"),
        (r"exec\s*\(", "exec()"),
        (r"DROP TABLE", "DROP TABLE"),
        (r"DELETE FROM", "DELETE FROM"),
        (r"rm -rf", "rm -rf"),
    ]
    for pat, desc in patterns:
        if re.search(pat, payload.code_diff):
            guardrail_hits.append(desc)
    if guardrail_hits:
        msg = f"GUARDRAIL BLOCKED: {', '.join(guardrail_hits)}"
        send_telegram_message(f"BLOCKED: {payload.file_path}\n{msg}")
        log_activity(f"Guardrail: {payload.file_path}", msg, "danger")
        return {"status": "BLOCKED", "message": msg, "findings": guardrail_hits}

    memory_ctx = retrieve_memory(payload.code_diff[:500])

    cwe_patterns = re.findall(r"CWE-\d+", payload.code_diff)
    kg_ctx = query_kg_context(cwe_patterns) if cwe_patterns else ""

    system_prompt = f"""You are EvoNet Guardian. Scan the Git diff for vulnerabilities.
If vulnerable: return ONLY the fixed pure code (no markdown, no explanation).
If safe: reply exactly SAFE.

Security knowledge:
{memory_ctx[:1000]}

Knowledge graph:
{kg_ctx[:500]}"""

    from ai_failover import ask_ai  # type: ignore[import-untyped]

    try:
        ai_reply, provider = ask_ai(
            f"{system_prompt}\n\nDiff from {payload.file_path}:\n{payload.code_diff[:3000]}",
            temperature=0.1,
            max_tokens=4096,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"All AI providers failed: {e}")

    latency = round(time.time() - start, 2)

    if ai_reply.strip() != "SAFE":
        pr_url = create_auto_pr(payload.repo, payload.commit_sha, payload.file_path, ai_reply)

        comment = f"**Vulnerability in `{payload.file_path}`**\nAI: {provider} | {latency}s"
        if pr_url:
            comment += f"\nAuto-PR: {pr_url}"
        post_github_comment(payload.repo, payload.commit_sha, comment)

        send_telegram_message(
            f"VULN: {payload.file_path}\n"
            f"Repo: {payload.repo} | {provider} | {latency}s\n"
            f"{'PR: ' + pr_url if pr_url else 'Patch ready'}"
        )
        log_activity(f"Vuln: {payload.file_path}", f"Fixed by {provider}", "danger")

        try:
            emb = get_embedding(ai_reply[:500])
            if emb:
                memory_index.upsert(
                    vectors=[{
                        "id": f"scan_{payload.commit_sha[:7]}_{int(time.time())}",
                        "values": emb,
                        "metadata": {"source": "api_scan", "file": payload.file_path, "text": ai_reply[:1000]},
                    }],
                    namespace="learned_skills",
                )
        except Exception:
            pass

        return {
            "status": "VULNERABILITY_FOUND",
            "provider": provider,
            "latency_seconds": latency,
            "pr_url": pr_url,
            "patch_preview": ai_reply[:200],
        }
    else:
        send_telegram_message(f"SAFE: {payload.file_path} ({provider}, {latency}s)")
        log_activity(f"Scan: {payload.file_path}", "Safe", "success")
        return {"status": "SAFE", "provider": provider, "latency_seconds": latency}


@app.post("/api/v1/scan/batch")
async def scan_batch(request: Request):
    data = await request.json()
    results = []
    for file_data in data.get("files", []):
        payload = ScanPayload(**file_data)
        result = await scan_code(payload)
        results.append({"file": payload.file_path, "result": result})
    return {"total": len(results), "results": results}


@app.post("/api/v1/approve")
async def approve_patch(request: Request):
    import shutil

    data = await request.json()
    action = data.get("action")
    draft = APP_DIR / "main_draft.py"
    target = APP_DIR / "main.py"
    backup_dir = PROJECT_ROOT / "logs" / "backups"

    if action == "approve" and draft.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"main_backup_{int(time.time())}.py"
        shutil.copy(target, backup)
        regex_blacklist_guardrail(draft.read_text())
        shutil.copy(draft, target)
        draft.unlink()
        send_telegram_message(f"PATCH APPROVED. Backup: {backup.name}")
        return {"status": "approved", "backup": str(backup)}
    elif action == "reject" and draft.exists():
        draft.unlink()
        send_telegram_message("PATCH REJECTED")
        return {"status": "rejected"}
    raise HTTPException(status_code=404, detail="No draft found")


@app.get("/api/v1/evolve")
async def trigger_evolution():
    import subprocess

    subprocess.Popen([sys.executable, str(APP_DIR / "scripts" / "self_evolve.py")])
    send_telegram_message("Evolution triggered via API")
    return {"status": "evolution_started"}


@app.get("/api/v1/status")
async def get_status():
    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("evonet-memory")
        ns = index.describe_index_stats().get("namespaces", {})
        return {
            "status": "online",
            "cves": ns.get("security_knowledge_clean", {}).get("vector_count", 0),
            "skills": ns.get("learned_skills", {}).get("vector_count", 0),
            "threats": ns.get("threat_intel_raw", {}).get("vector_count", 0),
        }
    except Exception:
        return {"status": "online", "pinecone": "unavailable"}


@app.get("/api/v1/search")
async def search_memory(q: str, namespace: str = "security_knowledge_clean"):
    try:
        query_vector = get_embedding(q)
        if not query_vector:
            return {"results": []}
        results = memory_index.query(vector=query_vector, top_k=5, namespace=namespace, include_metadata=True)
        return {
            "query": q,
            "results": [
                {"id": m["id"], "score": round(m["score"] * 100), "text": m.get("metadata", {}).get("text", "")[:300]}
                for m in results.get("matches", [])
            ],
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
