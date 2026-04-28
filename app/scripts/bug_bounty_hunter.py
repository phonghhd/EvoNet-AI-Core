import os
import json
import time
import requests
from typing import Dict, List
from datetime import datetime
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

class BugBountyHunter:
    """Hệ thống săn bug bounty tự động"""
    
    def __init__(self):
        self.bug_bounty_platforms = {
            "hackerone": "https://hackerone.com/programs/search.json",
            "bugcrowd": "https://bugcrowd.com/programs.json",
            "synack": "https://synack.com/programs"
        }
        self.found_bounties = []
    
    def search_bug_bounties(self) -> List[Dict]:
        """Tìm kiếm các chương trình bug bounty mới"""
        try:
            print("🔍 [BUG BOUNTY] Đang tìm kiếm chương trình bug bounty...")
            
            # Trong thực tế, bạn sẽ kết nối với các API của các nền tảng bug bounty
            # Ở đây chỉ là mô phỏng
            bounties = [
                {
                    "program": "Example Company API",
                    "bounty_range": "$100 - $5000",
                    "scope": ["api.example.com", "app.example.com"],
                    "severity": "high",
                    "last_updated": datetime.now().isoformat()
                },
                {
                    "program": "Web Application Test",
                    "bounty_range": "$50 - $1000",
                    "scope": ["test.example.com"],
                    "severity": "medium",
                    "last_updated": datetime.now().isoformat()
                }
            ]
            
            self.found_bounties = bounties
            return bounties
            
        except Exception as e:
            print(f"❌ Lỗi tìm kiếm bug bounty: {e}")
            return []
    
    def analyze_vulnerability(self, target_url: str, vulnerability_type: str) -> Dict:
        """Phân tích và tìm lỗ hổng tiềm năng"""
        try:
            # Mô phỏng phân tích lỗ hổng
            # Trong thực tế, bạn sẽ thực hiện các kiểm tra bảo mật thực sự
            analysis = {
                "target": target_url,
                "vulnerability_type": vulnerability_type,
                "severity": "high" if "sql" in vulnerability_type.lower() or "xss" in vulnerability_type.lower() else "medium",
                "description": f"Potential {vulnerability_type} vulnerability found on {target_url}",
                "recommendation": self.get_recommendation(vulnerability_type),
                "cvss_score": self.calculate_cvss(vulnerability_type)
            }
            
            return analysis
        except Exception as e:
            return {"error": f"Error analyzing vulnerability: {e}"}
    
    def get_recommendation(self, vuln_type: str) -> str:
        """Đưa ra khuyến nghị khắc phục cho lỗ hổng"""
        recommendations = {
            "sql_injection": "Use parameterized queries and input validation",
            "xss": "Sanitize user input and implement Content Security Policy",
            "csrf": "Implement anti-CSRF tokens and validate request origins",
            "file_inclusion": "Validate file paths and disable dangerous functions",
            "command_injection": "Input validation and avoid shell execution",
            "authentication_bypass": "Implement proper authentication and authorization",
            "insecure_deserialization": "Validate and sanitize all serialized data"
        }
        
        return recommendations.get(vuln_type.lower().replace(" ", "_"), "Implement proper security controls")
    
    def calculate_cvss(self, vuln_type: str) -> float:
        """Tính toán điểm CVSS cho lỗ hổng"""
        # Đây là bảng điểm CVSS đơn giản
        cvss_scores = {
            "sql_injection": 7.5,
            "xss": 6.1,
            "csrf": 8.1,
            "file_inclusion": 7.3,
            "command_injection": 9.0,
            "authentication_bypass": 9.8,
            "insecure_deserialization": 8.1
        }
        
        return cvss_scores.get(vuln_type.lower().replace(" ", "_"), 5.0)
    
    def generate_bug_report(self, analysis: Dict) -> str:
        """Tạo báo cáo bug bounty"""
        try:
            report = "🐛 <b>BUG HUNT REPORT:</b>\n"
            report += f"Target: {analysis.get('target', 'Unknown')}\n"
            report += f"Vulnerability Type: {analysis.get('vulnerability_type', 'Unknown')}\n"
            report += f"Severity: {analysis.get('severity', 'Unknown')}\n"
            report += f"CVSS Score: {analysis.get('cvss_score', 'N/A')}\n\n"
            
            report += "📋 <b>ANALYSIS:</b>\n"
            report += f"Description: {analysis.get('description', 'No description')}\n"
            report += f"Recommendation: {analysis.get('recommendation', 'No recommendation')}\n"
            
            return report
        except Exception as e:
            return f"❌ Error generating bug report: {e}"
    
    def submit_to_platform(self, report: str, platform: str) -> bool:
        """Gửi báo cáo đến nền tảng bug bounty"""
        try:
            print(f"📤 [BUG BOUNTY] Đang gửi báo cáo đến {platform}...")
            
            # Trong thực tế, bạn sẽ gửi đến API của nền tảng bug bounty
            # Ở đây chỉ là mô phỏng
            submission = {
                "platform": platform,
                "report": report,
                "timestamp": datetime.now().isoformat(),
                "status": "submitted"
            }
            
            print(f"✅ [BUG BOUNTY] Đã gửi báo cáo đến {platform}")
            return True
        except Exception as e:
            print(f"❌ Lỗi gửi báo cáo đến {platform}: {e}")
            return False

def main():
    """Main function"""
    print("🚀 [BUG BOUNTY] Khởi động hệ thống săn bug bounty...")
    
    # Tạo instance bug bounty hunter
    hunter = BugBountyHunter()
    
    # Tìm kiếm các chương trình bug bounty
    bounties = hunter.search_bug_bounties()
    
    if bounties:
        print(f"🎯 [BUG BOUNTY] Tìm thấy {len(bounties)} chương trình bug bounty")
        
        # Phân tích từng chương trình
        for i, bounty in enumerate(bounties[:3]):  # Chỉ phân tích 3 chương trình đầu
            print(f"🔍 [BUG BOUNTY] Đang phân tích {bounty['program']}...")
            
            # Phân tích lỗ hổng tiềm năng
            for target in bounty['scope'][:2]:  # Chỉ phân tích 2 target đầu
                analysis = hunter.analyze_vulnerability(target, "SQL Injection")
                
                # Tạo báo cáo
                report = hunter.generate_bug_report(analysis)
                
                # Gửi đến các nền tảng
                for platform in ["hackerone", "bugcrowd"]:
                    if hunter.submit_to_platform(report, platform):
                        print(f"✅ [BUG BOUNTY] Đã gửi báo cáo đến {platform}")
    else:
        print("✅ [BUG BOUNTY] Không tìm thấy chương trình bug bounty mới")
    
    print("✅ [BUG BOUNTY] Hoàn tất hệ thống săn bug bounty")

if __name__ == "__main__":
    main()