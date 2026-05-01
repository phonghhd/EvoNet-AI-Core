import pinecone
import os
from typing import List, Dict
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

class VectorStorage:
    """Vector database storage system using Pinecone"""
    
    def __init__(self):
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "evonet-memory")
        
        # Initialize Pinecone
        pinecone.init(api_key=self.pinecone_api_key, environment="us-west1-gcp")
        self.index = pinecone.Index(self.pinecone_index_name)
        
    def store_patch(self, cve_id: str, patch_data: Dict) -> str:
        """Store patch data in Pinecone vector database"""
        try:
            # Create a unique ID for this patch
            vector_id = f"patch_{cve_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[
                    {
                        "id": vector_id,
                        "values": self._generate_embedding(json.dumps(patch_data)),
                        "metadata": {
                            "cve_id": cve_id,
                            "patch_data": json.dumps(patch_data),
                            "type": "patch_knowledge",
                            "timestamp": datetime.now().isoformat()
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
        """Generate embedding for the text - placeholder implementation"""
        # In a real implementation, this would call an actual embedding model
        # For now, we'll return a fixed-size list of floats as placeholder
        return [0.0] * 768  # Pinecone expects 768 dimensions for the bge-base-en model
        
    def search_similar_patches(self, query_text: str, top_k: int = 5):
        """Search for similar patches in the vector database"""
        try:
            # Generate embedding for the query
            query_vector = self._generate_embedding(query_text)
            
            # Query the vector database for similar patches
            results = self.index.query(
                vector=query_vector,
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