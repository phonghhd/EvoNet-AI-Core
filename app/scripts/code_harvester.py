import os
from pinecone.pinecone import Pinecone
from dotenv import load_dotenv
import hashlib
import requests

load_dotenv("/app/.env", override=True)

WORKSPACE_DIR = "/workspace"
IGNORE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".next", "build", "dist"}
ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md"}


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
        print(f"Embedding error: {e}")
        return None


def chunk_text(text, max_chars=2000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]


def ingest_code():
    print("Starting code ingestion...")
    pc_key = os.getenv("PINECONE_API_KEY")
    if not pc_key:
        print("PINECONE_API_KEY not set, skipping")
        return

    pc = Pinecone(api_key=pc_key)
    index = pc.Index("evonet-memory")
    count = 0

    for root, dirs, files in os.walk(WORKSPACE_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    chunks = chunk_text(content)
                    vectors = []
                    for i, chunk in enumerate(chunks):
                        embedding = get_embedding(chunk)
                        if embedding:
                            doc_id = hashlib.md5(f"{file_path}_{i}".encode()).hexdigest()
                            vectors.append({
                                "id": doc_id,
                                "values": embedding,
                                "metadata": {
                                    "source": file_path,
                                    "type": "code",
                                    "language": ext,
                                    "text": chunk[:1000]
                                }
                            })

                    if vectors:
                        index.upsert(vectors=vectors, namespace="codebase")
                        print(f"Ingested: {file} ({len(vectors)} chunks)")
                        count += 1
                except Exception as e:
                    print(f"Skipping {file}: {e}")

    print(f"Done. Ingested {count} files into Pinecone.")


if __name__ == "__main__":
    ingest_code()
