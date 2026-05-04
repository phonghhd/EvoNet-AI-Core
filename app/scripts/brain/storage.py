import os
from typing import List, Dict
from dotenv import load_dotenv
import json
from datetime import datetime
import requests

load_dotenv("/app/.env", override=True)


class VectorStorage:
    def __init__(self):
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = "evonet-memory"
        self.pinecone_namespace = "patches"

        from pinecone import Pinecone
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index = self.pc.Index(self.pinecone_index_name)

    def _get_embedding(self, text: str) -> List[float]:
        cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_key = os.getenv("CLOUDFLARE_API_KEY")
        url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
        headers = {"Authorization": f"Bearer {cf_key}"}
        try:
            res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
            data = res.json()
            if data.get("success"):
                return data["result"]["data"][0]
        except Exception as e:
            print(f"Error generating embedding: {e}")
        return [0.0] * 768

    def store_patch_knowledge(self, cve_id: str, patch_data: dict) -> str:
        try:
            vector_id = f"patch_{cve_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            patch_text = json.dumps(patch_data, sort_keys=True)
            embedding = self._get_embedding(patch_text)

            self.index.upsert(
                vectors=[{
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "cve_id": cve_id,
                        "patch_data": patch_text[:1000],
                        "type": "patch_knowledge"
                    }
                }],
                namespace=self.pinecone_namespace
            )
            return vector_id
        except Exception as e:
            print(f"Error storing patch in Pinecone: {e}")
            return None

    def search_similar_patches(self, query_text: str, top_k: int = 5):
        try:
            query_vector = self._get_embedding(query_text)
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=self.pinecone_namespace,
                include_metadata=True
            )
            return results
        except Exception as e:
            print(f"Error searching similar patches: {e}")
            return None

    def query_patch_knowledge(self, query_vector, namespace="patches"):
        try:
            return self.index.query(
                vector=query_vector,
                top_k=5,
                namespace=namespace,
                include_metadata=True
            )
        except Exception as e:
            print(f"Error querying patch knowledge: {e}")
            return None


vector_storage = VectorStorage()
