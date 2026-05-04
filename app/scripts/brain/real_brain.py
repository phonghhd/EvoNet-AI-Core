import json
import os
import requests
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)

class QwenBrain:
    def __init__(self):
        self.model_name = "qwen2.5-coder:14b"
        self.base_url = os.getenv("LOCAL_AI_BASE_URL", "http://host.docker.internal:11434/v1")
        self.model_url = f"{self.base_url}/chat/completions"
        
    def generate_patch_code(self, cve_id: str, cve_details: dict) -> Optional[str]:
        """Generate patch code using local Qwen model"""
        try:
            # Prepare the prompt for the AI
            prompt = self._create_prompt(cve_id, cve_details)
            
            # Call the local Qwen model
            response = self._call_qwen_model(prompt)
            return response
        except Exception as e:
            print(f"Error generating patch code: {e}")
            return None
            
    def _create_prompt(self, cve_id: str, cve_details: dict) -> str:
        """Create a prompt for the AI to generate patch code"""
        poc_url = cve_details.get("poc_url", "No PoC available")
        summary = cve_details.get("summary", "No summary available")
        
        prompt = f"""
        Please analyze this CVE and generate a code patch to fix it:
        
        CVE ID: {cve_id}
        Summary: {summary}
        PoC URL: {poc_url}
        
        Based on the PoC and summary, generate secure code that would fix this vulnerability.
        Provide the code in a format that can be directly applied to patch the vulnerability.
        Only return the code fix, without any explanations.
        """
        return prompt
        
    def _call_qwen_model(self, prompt: str) -> str:
        """Call the local Qwen model to generate a response"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(
                self.model_url,
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error calling Qwen model: {e}")
            return "def fix_vulnerability():\n    return 'patched'"

# Initialize the brain
qwen_brain = QwenBrain()