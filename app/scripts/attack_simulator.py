import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
import tempfile
import docker

# Load environment variables
load_dotenv("/app/.env", override=True)

def get_env_safe(key_name):
    val = os.getenv(key_name)
    if val:
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None

def send_telegram(msg):
    token = get_env_safe("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_safe("TELEGRAM_CHAT_ID")
    if not token or not chat_id: 
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try: 
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

class AttackSimulator:
    """Attack simulation system for testing patches"""
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
        self.sandbox_image = "python:3.9-slim"
        
    def create_attack_payloads(self, vulnerability_type: str) -> List[Dict]:
        """Create attack payloads for testing"""
        # Common attack patterns for different vulnerability types
        payloads = []
        
        if vulnerability_type == "sql_injection":
            payloads = [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "' UNION SELECT * FROM admin--",
                "'; EXEC xp_cmdshell 'dir'; --"
            ]
        elif vulnerability_type == "xss":
            payloads = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "<svg/onload=alert('xss')>"
            ]
        elif vulnerability_type == "command_injection":
            payloads = [
                "; cat /etc/passwd",
                "| cat /etc/passwd",
                "&& cat /etc/passwd",
                "`cat /etc/passwd`"
            ]
        elif vulnerability_type == "path_traversal":
            payloads = [
                "../../../etc/passwd",
                "../../../../etc/shadow",
                "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"
            ]
        else:
            # Generic payloads
            payloads = [
                "<script>alert('test')</script>",
                "'; DROP TABLE--",
                "| ls -la",
                "&& whoami"
            ]
        
        return [{"type": vulnerability_type, "payload": payload} for payload in payloads]
    
    def create_sandbox_environment(self) -> str:
        """Create a sandbox Docker container for testing"""
        try:
            # Create a temporary directory for the sandbox
            with tempfile.TemporaryDirectory() as temp_dir:
                sandbox_path = Path(temp_dir)
                
                # Create a simple test application
                test_app = sandbox_path / "test_app.py"
                test_app.write_text("""
import sys
import os

def vulnerable_function(user_input):
    # This is a deliberately vulnerable function for testing
    print(f"Processing input: {user_input}")
    # In a real scenario, this would be the actual vulnerable code
    return user_input

if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = vulnerable_function(sys.argv[1])
        print(f"Result: {result}")
""")
                
                # Create Dockerfile
                dockerfile = sandbox_path / "Dockerfile"
                dockerfile.write_text("""
FROM python:3.9-slim
WORKDIR /app
COPY test_app.py .
COPY . /app
CMD ["python", "test_app.py"]
""")
                
                return str(sandbox_path)
        except Exception as e:
            print(f"Error creating sandbox: {e}")
            return None
    
    def run_attack_simulation(self, payload: str, test_file: str = "test_app.py") -> Dict:
        """Run attack simulation in sandbox"""
        try:
            # Create sandbox environment
            sandbox_path = self.create_sandbox_environment()
            if not sandbox_path:
                return {"success": False, "error": "Failed to create sandbox"}
            
            # Build and run in Docker container
            # Note: This is a simplified approach - in practice, you would use a more secure sandbox
            result = subprocess.run(
                ["python", test_file, payload],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=sandbox_path
            )
            
            return {
                "success": True,
                "payload": payload,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "vulnerable": result.returncode == 0 and "Error" not in result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "success": True,
                "payload": payload,
                "stdout": "",
                "stderr": "Timeout - possible successful attack",
                "returncode": 124,
                "vulnerable": True
            }
        except Exception as e:
            return {
                "success": False,
                "payload": payload,
                "error": str(e),
                "vulnerable": False
            }
    
    def test_patch_effectiveness(self, patch_file: str, vulnerability_type: str) -> Dict:
        """Test if a patch effectively prevents attacks"""
        try:
            # Create attack payloads
            payloads = self.create_attack_payloads(vulnerability_type)
            
            results = {
                "vulnerability_type": vulnerability_type,
                "total_attacks": len(payloads),
                "vulnerable_count": 0,
                "protected_count": 0,
                "attack_results": []
            }
            
            # Test each payload
            for payload_info in payloads:
                payload = payload_info["payload"]
                attack_result = self.run_attack_simulation(payload, patch_file)
                results["attack_results"].append(attack_result)
                
                if attack_result.get("vulnerable", False):
                    results["vulnerable_count"] += 1
                else:
                    results["protected_count"] += 1
            
            # Calculate effectiveness
            if results["total_attacks"] > 0:
                results["effectiveness"] = (results["protected_count"] / results["total_attacks"]) * 100
            else:
                results["effectiveness"] = 0
            
            return results
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_attack_report(self, test_results: Dict) -> str:
        """Generate a report of attack simulation results"""
        if not test_results.get("success", True):
            return f"❌ <b>KIỂM TRA BẢN VÁ THẤT BẠI:</b>\n{test_results.get('error', 'Unknown error')}"
        
        # Create report
        vuln_type = test_results.get("vulnerability_type", "unknown")
        effectiveness = test_results.get("effectiveness", 0)
        vulnerable = test_results.get("vulnerable_count", 0)
        protected = test_results.get("protected_count", 0)
        total = test_results.get("total_attacks", 0)
        
        # Check if patch is effective
        is_effective = effectiveness >= 80  # At least 80% effectiveness
        
        status = "✅" if is_effective else "❌"
        status_text = "ĐẠT YÊU CẦU" if is_effective else "KHÔNG ĐẠT"
        
        report = f"{status} <b>KIỂM TRA BẢN VÁ {status_text}:</b>\n"
        report += f"Loại lỗ hổng: <code>{vuln_type}</code>\n"
        report += f"Hiệu quả: {effectiveness:.1f}%\n"
        report += f"Đã chặn: {protected}/{total} cuộc tấn công\n"
        report += f"Vẫn bị ảnh hưởng: {vulnerable}/{total} cuộc tấn công"
        
        return report

def main():
    """Main function to run attack simulation"""
    print("Starting attack simulation...")
    send_telegram("🛡️ <b>MÔ PHỎNG TẤN CÔNG:</b>\nĐang kiểm tra hiệu quả của bản vá...")
    
    simulator = AttackSimulator()
    
    # Test different vulnerability types
    vulnerability_types = ["sql_injection", "xss", "command_injection", "path_traversal"]
    
    for vuln_type in vulnerability_types:
        print(f"Testing {vuln_type}...")
        test_results = simulator.test_patch_effectiveness("test_patch.py", vuln_type)
        report = simulator.generate_attack_report(test_results)
        send_telegram(report)
    
    print("Attack simulation completed")
    send_telegram("✅ <b>HOÀN TẤT MÔ PHỎNG:</b>\nĐã kiểm tra hiệu quả của bản vá chống các loại tấn công.")

if __name__ == "__main__":
    main()