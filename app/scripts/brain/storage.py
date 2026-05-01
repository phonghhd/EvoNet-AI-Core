import pinecone
import os
from typing import List, Dict
from dotenv import load_dotenv
import json
from datetime import datetime
import requests
from sentence_transformers import SentenceTransformer
import numpy as np

load_dotenv("./.env", override=True)

class VectorStorage:
    def __init__(self):
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = "evonet-memory"
        self.pinecone_namespace = "evonet-patches"
        
        # Initialize Pinecone
        self.pc = pinecone.Pinecone(api_key=self.pinecone_api_key)
        self.index = self.pc.Index("evonet-memory")
        
        # Initialize the embedding model
        self.embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        
    def store_patch_knowledge(self, cve_id: str, patch_data: dict):
        """Store patch data in Pinecone vector database"""
        try:
            # Create a unique ID for this patch
            vector_id = f"patch_{cve_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Convert patch data to string for embedding
            patch_text = json.dumps(patch_data, sort_keys=True)
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[
                    {
                        "id": vector_id,
                        "values": self._generate_embedding(patch_text).tolist(),
                        "metadata": {
                            "cve_id": cve_id,
                            "patch_data": patch_text,
                            "type": "patch_knowledge"
                        }
                    }
                ],
                namespace="patches"
            )
            return vector_id
        except Exception as e:
            print(f"Error storing patch in Pinecone: {e}")
            return None
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the text using sentence-transformers"""
        try:
            # Generate embedding using the model
            embedding = self.embedding_model.encode(text)
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return a zero vector as fallback
            return [0.0] * 384  # 384 is the dimension for paraphrase-MiniLM-L6-v2
        
    def search_similar_patches(self, query_text: str, top_k: int = 5):
        """Search for similar patches in the vector database"""
        try:
            # Generate embedding for the query
            query_vector = self._generate_embedding(query_text)
            
            # Query the vector database for similar patches
            results = self.index.query(
                vector=query_vector.tolist(),
                top_k=top_k,
                namespace="patches",
                include_metadata=True
            )
            return results
        except Exception as e:
            print(f"Error searching similar patches: {e}")
            return None

# Initialize the vector storage
vector_storage = VectorStorage()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the text - in production this would call an actual embedding model"""
        # This is a placeholder - in practice, you would use an actual embedding model
        # For now, we'll return a fixed-size list of floats as placeholder
        return [0.0] * 768  # Pinecone expects 768 dimensions for the bge-base-en model
        
    def search_similar_patches(self, cve_id: str, top_k: int = 5):
        """Search for similar patches in the vector database"""
        try:
            # Query the vector database for similar patches
            # (In practice, this would use actual embeddings)
            return []
        except Exception as e:
            print(f"Error searching similar patches: {e}")
            return []
            
    def query_patch_knowledge(self, query_vector, namespace="patches"):
        """Query patch knowledge from Pinecone"""
        try:
            # Query the vector database for similar patches
            return self.index.query(
                vector=query_vector,
                top_k=5,
                namespace=namespace
            )
        except Exception as e:
            print(f"Error querying patch knowledge: {e}")
            return None
        return None

# Initialize the vector storage
vector_storage = VectorStorage()