import os
import requests
import json
from typing import List, Dict
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)


class AdvancedRAG:
    def __init__(self):
        self.pinecone_key = os.getenv("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=self.pinecone_key)
        self.index = self.pc.Index("evonet-memory")

    def get_embedding(self, text: str) -> List[float]:
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

    def retrieve(self, query: str, namespace: str = "security_knowledge_clean", top_k: int = 5) -> List[Dict]:
        query_emb = self.get_embedding(query)
        if not query_emb:
            return []

        results = self.index.query(
            vector=query_emb,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True
        )
        return results.get('matches', [])

    def retrieve_multi_namespace(self, query: str, namespaces: List[str] = None, top_k: int = 5) -> List[Dict]:
        if namespaces is None:
            namespaces = ["security_knowledge_clean", "learned_skills", "threat_intel_raw"]

        all_results = []
        for ns in namespaces:
            results = self.retrieve(query, namespace=ns, top_k=top_k)
            for r in results:
                r['namespace'] = ns
            all_results.extend(results)

        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return all_results[:top_k]


class ContextualRanker:
    def __init__(self):
        self.weights = {'recency': 0.3, 'relevance': 0.5, 'popularity': 0.2}

    def rerank(self, query: str, documents: List[Dict], context: Dict = None) -> List[Dict]:
        if context is None:
            context = {}

        urgency = context.get('urgency', 'normal')
        if urgency == 'high':
            self.weights['recency'] = 0.5
            self.weights['relevance'] = 0.3

        import datetime
        for doc in documents:
            recency_score = 0.5
            doc_date = doc.get('metadata', {}).get('date', '')
            if doc_date:
                try:
                    doc_dt = datetime.datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                    days_old = (datetime.datetime.now(datetime.timezone.utc) - doc_dt).days
                    recency_score = max(0.1, 1.0 - (days_old / 365))
                except Exception:
                    pass

            relevance_score = doc.get('score', 0.5)
            popularity_score = min(1.0, doc.get('metadata', {}).get('usage_count', 1) / 100.0)

            doc['contextual_score'] = (
                self.weights['recency'] * recency_score +
                self.weights['relevance'] * relevance_score +
                self.weights['popularity'] * popularity_score
            )

        documents.sort(key=lambda x: x['contextual_score'], reverse=True)
        return documents
