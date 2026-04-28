import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pinecone.pinecone import Pinecone
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/phong/evonet-core/.env", override=True)

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
    """Threat alert system for monitoring and alerting on new security threats"""
    
    def __init__(self):
        self.pinecone_key = get_env_safe("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=self.pinecone_key)
        self.index = self.pc.Index("evonet-memory")
        
    def get_embedding(self, text: str):
        """Get embedding from Cloudflare"""
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
        """Check for new CVEs in threat intelligence data"""
        try:
            # Query Pinecone for recent threat intel data
            # We'll look for data from the last 24 hours
            dummy_vector = [0.0] * 768  # Placeholder for query
            results = self.index.query(
                vector=dummy_vector,
                top_k=100,  # Get recent items
                namespace="threat_intel_raw",
                include_metadata=True
            )
            
            new_cves = []
            if results.get('matches'):
                # Filter for recent items (last 24 hours)
                one_day_ago = datetime.now() - timedelta(days=1)
                
                for match in results['matches']:
                    metadata = match.get('metadata', {})
                    # Check if this is a CVE entry
                    if 'cve_ids' in metadata or 'cve' in metadata.get('title', '').lower():
                        # Parse date if available
                        date_str = metadata.get('date', '')
                        if date_str:
                            try:
                                # Try to parse the date
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
                            except:
                                # If we can't parse date, skip this entry
                                pass
            
            return new_cves
        except Exception as e:
            print(f"Error checking new CVEs: {e}")
            return []
    
    def analyze_threat_level(self, threat_data: List[Dict[str, Any]]) -> str:
        """Analyze threat level based on collected data"""
        if not threat_data:
            return "low"
        
        # Count critical items
        critical_count = 0
        high_count = 0
        medium_count = 0
        
        # For now, we'll use a simple heuristic
        # In a real implementation, this would use ML models
        for item in threat_data:
            title = item.get('title', '').lower()
            if 'critical' in title or 'severe' in title:
                critical_count += 1
            elif 'high' in title or 'important' in title:
                high_count += 1
            else:
                medium_count += 1
        
        # Determine threat level
        if critical_count > 0:
            return "critical"
        elif high_count > 2:
            return "high"
        elif medium_count > 5:
            return "medium"
        else:
            return "low"
    
    def generate_alert_message(self, threat_data: List[Dict[str, Any]], threat_level: str) -> str:
        """Generate alert message for Telegram"""
        if not threat_data:
            return ""
        
        # Count total threats
        total_threats = len(threat_data)
        
        # Get unique sources
        sources = list(set([item['source'] for item in threat_data]))
        
        # Generate message based on threat level
        if threat_level == "critical":
            level_emoji = "🔴"
            level_text = "MỨC ĐỘ CAO"
        elif threat_level == "high":
            level_emoji = "🟠"
            level_text = "MỨC ĐỘ TRUNG BÌNH-CAO"
        else:
            level_emoji = "🟡"
            level_text = "MỨC ĐỘ TRUNG BÌNH"
        
        # Create message
        message = f"{level_emoji} <b>CẢNH BÁO BẢO MẬT MỚI</b>\n"
        message += f"Phát hiện {total_threats} mối đe dọa mới từ {', '.join(sources)}\n"
        message += f"Mức độ: <b>{level_text}</b>\n\n"
        
        # Add top 3 threats
        for i, threat in enumerate(threat_data[:3]):
            cve_info = f" ({', '.join(threat.get('cve_ids', []))})" if threat.get('cve_ids') else ""
            message += f"{i+1}. {threat['title']}{cve_info}\n"
        
        if len(threat_data) > 3:
            message += f"\n... và {len(threat_data) - 3} mối đe dọa khác"
        
        return message
    
    def check_and_alert(self):
        """Check for new threats and send alerts if needed"""
        try:
            # Check for new CVEs
            new_cves = self.check_new_cves()
            
            if new_cves:
                # Analyze threat level
                threat_level = self.analyze_threat_level(new_cves)
                
                # Generate and send alert
                alert_msg = self.generate_alert_message(new_cves, threat_level)
                if alert_msg:
                    send_telegram(alert_msg)
                    print("Alert sent successfully")
                else:
                    print("No alert generated")
            else:
                print("No new threats detected")
                
        except Exception as e:
            print(f"Error in threat alert system: {e}")
            # Send error alert
            send_tele("⚠️ <b>LỖI HỆ THỐNG:</b>\nHệ thống cảnh báo gặp lỗi: {e}")

def main():
    """Main function to run threat alert system"""
    print("Starting threat alert system...")
    send_telegram("🔔 <b>HỆ THỐNG CẢNH BÁO BẢO MẬT:</b>\nĐang kiểm tra các mối đe dọa mới...")
    
    alert_system = ThreatAlertSystem()
    alert_system.check_and_alert()
    
    print("Threat alert system completed")
    send_telegram("✅ <b>HOÀN TẤT KIỂM TRA:</b>\nHệ thống cảnh báo đã hoàn tất kiểm tra.")

if __name__ == "__main__":
    main()