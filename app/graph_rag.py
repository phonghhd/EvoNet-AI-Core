import os
import requests
from typing import List, Dict, Optional
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)


class GraphRAG:
    """Combines Neo4j Knowledge Graph with Pinecone Vector Retrieval for richer context"""

    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index("evonet-memory")
        self._kg = None

    @property
    def kg(self):
        if self._kg is None:
            try:
                from kg_manager import get_kg_instance
                self._kg = get_kg_instance()
            except Exception:
                self._kg = None
        return self._kg

    def get_embedding(self, text: str) -> Optional[List[float]]:
        cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_key = os.getenv("CLOUDFLARE_API_KEY")
        url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
        headers = {"Authorization": f"Bearer {cf_key}"}
        try:
            res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
            data = res.json()
            if data.get("success"):
                return data["result"]["data"][0]
        except Exception:
            pass
        return None

    def vector_search(self, query: str, namespace: str = "security_knowledge_clean", top_k: int = 5) -> List[Dict]:
        embedding = self.get_embedding(query)
        if not embedding:
            return []
        results = self.index.query(
            vector=embedding, top_k=top_k,
            namespace=namespace, include_metadata=True
        )
        return results.get('matches', [])

    def graph_search(self, cve_id: str) -> Dict:
        if not self.kg or self.kg.driver is None:
            return {"defenses": [], "related_cves": []}

        defenses = self.kg.get_defenses_for_cve(cve_id)
        related = self.kg.get_related_cves(cve_id)
        return {"defenses": defenses, "related_cves": related}

    def graph_expand_context(self, cve_ids: List[str]) -> str:
        context_parts = []
        for cve_id in cve_ids:
            graph_data = self.graph_search(cve_id)
            if graph_data["defenses"]:
                defenses = [d.get("description", "")[:200] for d in graph_data["defenses"][:3]]
                context_parts.append(f"Known defenses for {cve_id}: {'; '.join(defenses)}")
            if graph_data["related_cves"]:
                related = [r.get("cve_id", "") for r in graph_data["related_cves"][:3]]
                context_parts.append(f"Related CVEs: {', '.join(related)}")
        return "\n".join(context_parts)

    def retrieve(self, query: str, namespace: str = "security_knowledge_clean", top_k: int = 5) -> str:
        vector_results = self.vector_search(query, namespace, top_k)
        if not vector_results:
            return ""

        context_parts = []
        cve_ids_found = []

        for match in vector_results:
            score = round(match.get('score', 0) * 100)
            text = match.get('metadata', {}).get('text', '')
            cve_id = match.get('id', '')
            if cve_id.startswith('CVE-'):
                cve_ids_found.append(cve_id)
            context_parts.append(f"[Vector Match {score}%] {text[:500]}")

        if cve_ids_found and self.kg and self.kg.driver is not None:
            graph_context = self.graph_expand_context(cve_ids_found)
            if graph_context:
                context_parts.append(f"\n[Knowledge Graph Context]\n{graph_context}")

        return "\n---\n".join(context_parts)

    def retrieve_multi_namespace(self, query: str, top_k: int = 5) -> str:
        namespaces = ["security_knowledge_clean", "learned_skills", "threat_intel_raw"]
        all_context = []
        for ns in namespaces:
            ctx = self.retrieve(query, ns, top_k=3)
            if ctx:
                all_context.append(f"[{ns}]\n{ctx}")
        return "\n\n".join(all_context)


_graph_rag = None


def get_graph_rag():
    global _graph_rag
    if _graph_rag is None:
        _graph_rag = GraphRAG()
    return _graph_rag
