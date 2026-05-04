import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List
import requests
from dotenv import load_dotenv

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
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception:
        pass


class AttackSimulator:
    PAYLOADS = {
        "sql_injection": [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM admin--",
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<svg/onload=alert('xss')>",
        ],
        "command_injection": [
            "; cat /etc/passwd",
            "| cat /etc/passwd",
            "&& whoami",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        ],
    }

    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)

    def create_attack_payloads(self, vulnerability_type: str) -> List[Dict]:
        payloads = self.PAYLOADS.get(vulnerability_type, self.PAYLOADS["sql_injection"])
        return [{"type": vulnerability_type, "payload": p} for p in payloads]

    def run_attack_simulation(self, test_file: str, payload: str) -> Dict:
        try:
            result = subprocess.run(
                ["python", test_file, payload],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.workspace_path)
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
            return {"success": True, "payload": payload, "returncode": 124, "vulnerable": True}
        except Exception as e:
            return {"success": False, "payload": payload, "error": str(e), "vulnerable": False}

    def test_patch_effectiveness(self, patch_file: str, vulnerability_type: str) -> Dict:
        payloads = self.create_attack_payloads(vulnerability_type)
        results = {
            "vulnerability_type": vulnerability_type,
            "total_attacks": len(payloads),
            "vulnerable_count": 0,
            "protected_count": 0,
            "attack_results": []
        }
        for p in payloads:
            result = self.run_attack_simulation(patch_file, p["payload"])
            results["attack_results"].append(result)
            if result.get("vulnerable", False):
                results["vulnerable_count"] += 1
            else:
                results["protected_count"] += 1

        total = results["total_attacks"]
        results["effectiveness"] = (results["protected_count"] / total * 100) if total > 0 else 0
        return results

    def generate_attack_report(self, test_results: Dict) -> str:
        vuln_type = test_results.get("vulnerability_type", "unknown")
        effectiveness = test_results.get("effectiveness", 0)
        total = test_results.get("total_attacks", 0)
        protected = test_results.get("protected_count", 0)
        vulnerable = test_results.get("vulnerable_count", 0)
        is_effective = effectiveness >= 80

        status = "✅" if is_effective else "❌"
        text = "PASS" if is_effective else "FAIL"
        report = f"{status} <b>PATCH TEST {text}:</b>\n"
        report += f"Type: <code>{vuln_type}</code>\n"
        report += f"Effectiveness: {effectiveness:.1f}%\n"
        report += f"Blocked: {protected}/{total} | Vulnerable: {vulnerable}/{total}"
        return report


def main():
    print("Starting attack simulation...")
    send_telegram("🛡️ <b>ATTACK SIMULATION:</b>\nTesting patch effectiveness...")
    simulator = AttackSimulator()

    for vuln_type in ["sql_injection", "xss", "command_injection", "path_traversal"]:
        results = simulator.test_patch_effectiveness("test_patch.py", vuln_type)
        report = simulator.generate_attack_report(results)
        send_telegram(report)
        print(f"{vuln_type}: {results['effectiveness']:.1f}% effective")

    print("Attack simulation completed")


if __name__ == "__main__":
    main()
