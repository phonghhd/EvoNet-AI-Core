import requests
import json
from typing import Dict, List
from datetime import datetime, timedelta
import feedparser
import time
import os
from dotenv import load_dotenv

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

class ThreatIntelligenceCollector:
    """Hệ thống thu thập Threat Intelligence từ nhiều nguồn"""
    
    def __init__(self):
        self.threat_data = []
        self.sources = {
            "cve": "https://cve.circl.lu/api/last",
            "exploit_db": "https://www.exploit-db.com/rss.xml",
            "alienvault": "https://otx.alienvault.com/indicator/export"
        }
    
    def collect_cve_threats(self) -> List[Dict]:
        """Thu thập CVE mới từ Circl.lu"""
        try:
            print("🔍 [THREAT INTEL] Đang thu thập CVE mới...")
            response = requests.get(self.sources["cve"], timeout=30)
            if response.status_code == 200:
                cve_data = response.json()
                threats = []
                for item in cve_data[:10]:  # Chỉ lấy 10 CVE mới nhất
                    threats.append({
                        "type": "CVE",
                        "id": item.get("id", "Unknown"),
                        "summary": item.get("summary", "No summary"),
                        "cvss": item.get("cvss", "N/A"),
                        "references": item.get("references", []),
                        "published": item.get("Published", "N/A"),
                        "source": "CIRCL.lu"
                    })
                return threats
            else:
                print(f"❌ Lỗi thu thập CVE: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Lỗi thu thập CVE: {e}")
            return []
    
    def collect_exploit_db_threats(self) -> List[Dict]:
        """Thu thập Exploit từ Exploit-DB"""
        try:
            print("🔍 [THREAT INTEL] Đang thu thập Exploit-DB...")
            feed = feedparser.parse(self.sources["exploit_db"])
            threats = []
            for entry in feed.entries[:10]:  # Chỉ lấy 10 exploit mới nhất
                threats.append({
                    "type": "Exploit",
                    "title": entry.title,
                    "description": entry.description,
                    "link": entry.link,
                    "published": entry.published,
                    "source": "Exploit-DB"
                })
            return threats
        except Exception as e:
            print(f"❌ Lỗi thu thập Exploit-DB: {e}")
            return []
    
    def collect_alienvault_threats(self) -> List[Dict]:
        """Thu thập threat intel từ AlienVault OTX"""
        try:
            print("🔍 [THREAT INTEL] Đang thu thập AlienVault OTX...")
            # Trong thực tế, bạn cần API key để truy cập
            # Ở đây chỉ là mô phỏng
            threats = []
            for i in range(5):  # Mô phỏng 5 threat
                threats.append({
                    "type": "Indicator",
                    "title": f"Malicious IP {i+1}",
                    "description": f"IP address flagged as malicious",
                    "indicator": f"192.168.1.{100+i}",
                    "type_name": "IPv4",
                    "source": "AlienVault OTX"
                })
            return threats
        except Exception as e:
            print(f"❌ Lỗi thu thập AlienVault: {e}")
            return []
    
    def collect_all_threats(self) -> List[Dict]:
        """Thu thập threat intel từ tất cả các nguồn"""
        print("🔍 [THREAT INTEL] Bắt đầu thu thập threat intelligence...")
        
        all_threats = []
        all_threats.extend(self.collect_cve_threats())
        all_threats.extend(self.collect_exploit_db_threats())
        all_threats.extend(self.collect_alienvault_threats())
        
        self.threat_data = all_threats
        print(f"✅ [THREAT INTEL] Hoàn tất thu thập. Tìm thấy {len(all_threats)} threat")
        return all_threats
    
    def generate_threat_report(self) -> str:
        """Tạo báo cáo threat intel"""
        report = "📡 <b>BÁO CÁO THREAT INTEL:</b>\n"
        report += f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Tổng số threat tìm thấy: {len(self.threat_data)}\n\n"
        
        # Phân loại theo loại threat
        threat_types = {}
        for threat in self.threat_data:
            threat_type = threat.get("type", "Unknown")
            if threat_type not in threat_types:
                threat_types[threat_type] = []
            threat_types[threat_type].append(threat)
        
        for threat_type, threats in threat_types.items():
            report += f"📊 {threat_type}: {len(threats)} threat\n"
        
        report += "\n📋 Threat mới nhất:\n"
        
        # Liệt kê 5 threat mới nhất
        for i, threat in enumerate(self.threat_data[:5], 1):
            report += f"{i}. 🔴 {threat.get('type', 'Unknown')}: {threat.get('title', threat.get('id', 'N/A'))}\n"
            if "summary" in threat:
                summary = threat["summary"][:100] + "..." if len(threat["summary"]) > 100 else threat["summary"]
                report += f"   Mô tả: {summary}\n"
            if "cvss" in threat and threat["cvss"] != "N/A":
                report += f"   CVSS: {threat['cvss']}\n"
            report += f"   Nguồn: {threat.get('source', 'Unknown')}\n\n"
        
        if len(self.threat_data) > 5:
            report += f"... và {len(self.threat_data) - 5} threat khác\n"
        
        return report
    
    def get_actionable_intel(self) -> str:
        """Tạo intelligence có thể hành động"""
        actionable = "⚡ <b>THREAT ACTIONABLE:</b>\n"
        actionable += "Các threat cần chú ý ngay:\n\n"
        
        # Lọc các threat nghiêm trọng
        critical_threats = [t for t in self.threat_data if t.get("cvss", 0) and (isinstance(t.get("cvss"), (int, float)) and t["cvss"] >= 7.0)]
        
        if critical_threats:
            actionable += "🔴 Threat nghiêm trọng (CVSS >= 7.0):\n"
            for threat in critical_threats[:3]:
                actionable += f"• {threat.get('id', threat.get('title', 'Unknown'))}\n"
                actionable += f"  CVSS: {threat.get('cvss', 'N/A')}\n"
                actionable += f"  Mô tả: {threat.get('summary', 'No description')[:50]}...\n\n"
        else:
            actionable += "✅ Không có threat nghiêm trọng nào được phát hiện\n"
        
        return actionable

def main():
    """Main function"""
    print("🚀 [THREAT INTEL] Khởi động hệ thống Threat Intelligence...")
    send_telegram("📡 <b>HỆ THỐNG THREAT INTEL:</b> Đang bắt đầu thu thập threat intelligence...")
    
    # Tạo collector instance
    collector = ThreatIntelligenceCollector()
    
    # Thu thập threat intel
    threats = collector.collect_all_threats()
    
    # Tạo và gửi báo cáo
    threat_report = collector.generate_threat_report()
    send_telegram(threat_report)
    
    # Gửi intelligence có thể hành động
    actionable_intel = collector.get_actionable_intel()
    send_telegram(actionable_intel)
    
    print("✅ [THREAT INTEL] Hoàn tất thu thập threat intelligence")
    send_telegram("✅ <b>THREAT INTEL HOÀN TẤT:</b> Đã hoàn tất quá trình thu thập threat intelligence")

if __name__ == "__main__":
    main()