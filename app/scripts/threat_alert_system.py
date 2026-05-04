import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pinecone.pinecone import Pinecone
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
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")


class ThreatAlertSystem:
    def __init__(self):
        self.pinecone_key = get_env_safe("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=self.pinecone_key)
        self.index = self.pc.Index("evonet-memory")

    def get_embedding(self, text: str):
        cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
        cf_key = get_env_safe("CLOUDFLARE_API_KEY")
        url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
        headers = {"Authorization": f"Bearer {cf_key}"}
        try:
            res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
            data = res.json()
            if data.get("success"):
                return data["result"]["data"][0]
            return None
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None

    def check_new_cves(self) -> List[Dict[str, Any]]:
        try:
            query_vector = self.get_embedding("latest security threats CVE vulnerabilities")
            if not query_vector:
                return []

            results = self.index.query(
                vector=query_vector,
                top_k=50,
                namespace="threat_intel_raw",
                include_metadata=True
            )

            new_cves = []
            if results.get('matches'):
                one_day_ago = datetime.now() - timedelta(days=1)
                for match in results['matches']:
                    metadata = match.get('metadata', {})
                    if match.get('score', 0) < 0.3:
                        continue
                    date_str = metadata.get('date', '')
                    if date_str:
                        try:
                            entry_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            if entry_date >= one_day_ago:
                                new_cves.append({
                                    'id': match.get('id'),
                                    'title': metadata.get('title'),
                                    'date': date_str,
                                    'link': metadata.get('link'),
                                    'source': metadata.get('source'),
                                    'cve_ids': metadata.get('cve_ids', [])
                                })
                        except Exception:
                            pass
            return new_cves
        except Exception as e:
            print(f"Error checking new CVEs: {e}")
            return []

    def analyze_threat_level(self, threat_data: List[Dict[str, Any]]) -> str:
        if not threat_data:
            return "low"
        critical_count = sum(1 for t in threat_data if 'critical' in t.get('title', '').lower() or 'severe' in t.get('title', '').lower())
        high_count = sum(1 for t in threat_data if 'high' in t.get('title', '').lower() or 'important' in t.get('title', '').lower())
        if critical_count > 0:
            return "critical"
        elif high_count > 2:
            return "high"
        elif len(threat_data) > 5:
            return "medium"
        return "low"

    def generate_alert_message(self, threat_data: List[Dict[str, Any]], threat_level: str) -> str:
        if not threat_data:
            return ""
        level_map = {
            "critical": ("🔴", "CRITICAL"),
            "high": ("🟠", "HIGH"),
            "medium": ("🟡", "MEDIUM"),
            "low": ("🟢", "LOW")
        }
        emoji, text = level_map.get(threat_level, ("🟢", "LOW"))
        sources = list(set(t.get('source', 'Unknown') for t in threat_data))
        msg = f"{emoji} <b>SECURITY ALERT</b>\n"
        msg += f"Detected {len(threat_data)} new threats from {', '.join(sources)}\n"
        msg += f"Level: <b>{text}</b>\n\n"
        for i, threat in enumerate(threat_data[:3]):
            cve_info = f" ({', '.join(threat.get('cve_ids', []))})" if threat.get('cve_ids') else ""
            msg += f"{i+1}. {threat['title']}{cve_info}\n"
        if len(threat_data) > 3:
            msg += f"\n... and {len(threat_data) - 3} more threats"
        return msg

    def check_and_alert(self):
        try:
            new_cves = self.check_new_cves()
            if new_cves:
                threat_level = self.analyze_threat_level(new_cves)
                alert_msg = self.generate_alert_message(new_cves, threat_level)
                if alert_msg:
                    send_telegram(alert_msg)
                    print("Alert sent successfully")
            else:
                print("No new threats detected")
        except Exception as e:
            print(f"Error in threat alert system: {e}")
            send_telegram(f"⚠️ <b>SYSTEM ERROR:</b>\nAlert system error: {e}")


def main():
    print("Starting threat alert system...")
    send_telegram("🔔 <b>THREAT ALERT SYSTEM:</b>\nChecking for new threats...")
    alert_system = ThreatAlertSystem()
    alert_system.check_and_alert()
    print("Threat alert system completed")


if __name__ == "__main__":
    main()
