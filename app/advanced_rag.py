import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Tuple
from pinecone import Pinecone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/app/.env", override=True)

class NeuralRanker(nn.Module):
    """Neural network for advanced ranking and reranking"""
    
    def __init__(self, input_dim: int = 768, hidden_dim: int = 512, output_dim: int = 1):
        super(NeuralRanker, self).__init__()
        
        # Neural network architecture for ranking
        self.ranker = nn.Sequential(
            nn.Linear(input_dim * 2, hidden_dim),  # Query and document embeddings
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Sigmoid()  # Output probability between 0 and 1
        )
        
    def forward(self, query_emb: torch.Tensor, doc_emb: torch.Tensor) -> torch.Tensor:
        """Forward pass to compute relevance score"""
        # Concatenate query and document embeddings
        combined = torch.cat([query_emb, doc_emb], dim=1)
        return self.ranker(combined)

class AdvancedRAG:
    """Advanced Retrieval-Augmented Generation with neural ranking"""
    
    def __init__(self):
        self.pinecone_key = os.getenv("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=self.pinecone_key)
        self.index = self.pc.Index("evonet-memory")
        
        # Initialize neural ranker
        self.ranker = NeuralRanker()
        
        # Load pre-trained model if available
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained neural ranking model"""
        try:
            model_path = "/app/models/neural_ranker.pth"
            if os.path.exists(model_path):
                self.ranker.load_state_dict(torch.load(model_path))
                print("Loaded pre-trained neural ranking model")
            else:
                print("No pre-trained model found, using initialized model")
        except Exception as e:
            print(f"Error loading neural ranking model: {e}")
    
    def _save_model(self):
        """Save trained neural ranking model"""
        try:
            model_path = "/app/models"
            os.makedirs(model_path, exist_ok=True)
            torch.save(self.ranker.state_dict(), f"{model_path}/neural_ranker.pth")
            print("Saved neural ranking model")
        except Exception as e:
            print(f"Error saving neural ranking model: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Cloudflare"""
        try:
            import requests
            cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
            cf_key = os.getenv("CLOUDFLARE_API_KEY")
            url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
            headers = {"Authorization": f"Bearer {cf_key}"}
            
            res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
            data = res.json()
            if data.get("success"):
                return data["result"]["data"][0]
            return None
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    def neural_rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        """Rerank documents using neural network"""
        try:
            # Get query embedding
            query_emb = self.get_embedding(query)
            if not query_emb:
                return documents
            
            # Convert to tensor
            query_tensor = torch.tensor([query_emb], dtype=torch.float32)
            
            # Rerank documents
            reranked_docs = []
            for doc in documents:
                # Get document embedding
                doc_text = doc.get('metadata', {}).get('text', '')
                doc_emb = self.get_embedding(doc_text)
                
                if doc_emb:
                    # Convert to tensor
                    doc_tensor = torch.tensor([doc_emb], dtype=torch.float32)
                    
                    # Get relevance score from neural ranker
                    with torch.no_grad():
                        score = self.ranker(query_tensor, doc_tensor).item()
                    
                    # Add score to document
                    doc['neural_score'] = score
                    reranked_docs.append(doc)
                else:
                    doc['neural_score'] = 0.0
                    reranked_docs.append(doc)
            
            # Sort by neural score
            reranked_docs.sort(key=lambda x: x['neural_score'], reverse=True)
            return reranked_docs
            
        except Exception as e:
            print(f"Error in neural reranking: {e}")
            return documents
    
    def retrieve_with_neural_ranking(self, query: str, namespace: str = "security_knowledge_clean", top_k: int = 10) -> List[Dict]:
        """Retrieve and rerank documents using neural ranking"""
        try:
            # Get query embedding
            query_emb = self.get_embedding(query)
            if not query_emb:
                return []
            
            # Retrieve initial candidates from Pinecone
            results = self.index.query(
                vector=query_emb,
                top_k=top_k * 2,  # Retrieve more candidates for reranking
                namespace=namespace,
                include_metadata=True
            )
            
            if not results.get('matches'):
                return []
            
            # Apply neural reranking
            reranked = self.neural_rerank(query, results['matches'])
            
            # Return top_k after reranking
            return reranked[:top_k]
            
        except Exception as e:
            print(f"Error in retrieval with neural ranking: {e}")
            return []

class ContextualRanker:
    """Context-aware ranking system"""
    
    def __init__(self):
        self.context_weights = {
            'recency': 0.3,
            'relevance': 0.5,
            'popularity': 0.2
        }
    
    def contextual_rerank(self, query: str, documents: List[Dict], context: Dict = None) -> List[Dict]:
        """Rerank documents based on contextual factors"""
        if context is None:
            context = {}
        
        # Extract context factors
        user_role = context.get('user_role', 'default')
        urgency = context.get('urgency', 'normal')
        domain = context.get('domain', 'general')
        
        # Adjust weights based on context
        if user_role == 'admin':
            self.context_weights['recency'] = 0.4
            self.context_weights['relevance'] = 0.4
            self.context_weights['popularity'] = 0.2
        elif urgency == 'high':
            self.context_weights['recency'] = 0.5
            self.context_weights['relevance'] = 0.3
            self.context_weights['popularity'] = 0.2
        
        # Apply contextual reranking
        for doc in documents:
            # Calculate recency score (newer documents get higher scores)
            import datetime
            try:
                doc_date = doc.get('metadata', {}).get('date', '')
                if doc_date:
                    doc_datetime = datetime.datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                    days_old = (datetime.datetime.now(datetime.timezone.utc) - doc_datetime).days
                    recency_score = max(0.1, 1.0 - (days_old / 365))  # Decay over a year
                else:
                    recency_score = 0.5
            except:
                recency_score = 0.5
            
            # Calculate popularity score (based on usage/frequency)
            popularity_score = doc.get('metadata', {}).get('usage_count', 1) / 100.0
            popularity_score = min(1.0, popularity_score)
            
            # Calculate relevance score (from Pinecone)
            relevance_score = doc.get('score', 0.5)
            
            # Combine scores with context weights
            contextual_score = (
                self.context_weights['recency'] * recency_score +
                self.context_weights['relevance'] * relevance_score +
                self.context_weights['popularity'] * popularity_score
            )
            
            doc['contextual_score'] = contextual_score
        
        # Sort by contextual score
        documents.sort(key=lambda x: x['contextual_score'], reverse=True)
        return documents

def main():
    """Example usage of advanced RAG system"""
    print("Initializing Advanced RAG system...")
    
    # Initialize systems
    advanced_rag = AdvancedRAG()
    contextual_ranker = ContextualRanker()
    
    # Example query
    query = "SQL injection prevention best practices"
    
    # Retrieve with neural ranking
    results = advanced_rag.retrieve_with_neural_ranking(query)
    
    # Apply contextual reranking
    context = {
        'user_role': 'developer',
        'urgency': 'normal',
        'domain': 'web_security'
    }
    
    contextual_results = contextual_ranker.contextual_rerank(query, results, context)
    
    print(f"Retrieved {len(contextual_results)} documents with advanced ranking")
    
    # Print top results
    for i, doc in enumerate(contextual_results[:5]):
        print(f"{i+1}. {doc.get('metadata', {}).get('title', 'Untitled')} (Score: {doc.get('contextual_score', 0):.3f})")

if __name__ == "__main__":
    main()