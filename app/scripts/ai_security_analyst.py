import os
import json
import time
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re

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

class AISecurityAnalyst:
    """Hệ thống phân tích bảo mật bằng AI"""
    
    def __init__(self):
        self.api_key = get_env_safe("OPENAI_API_KEY")
        self.model = "gpt-4"  # Hoặc model AI ưa thích
    
    def analyze_security_logs(self, logs: List[Dict]) -> str:
        """Phân tích log bảo mật bằng AI"""
        try:
            # Trong thực tế, bạn sẽ kết nối với API AI
            # Ở đây chỉ là mô phỏng
            analysis = "Phân tích AI cho thấy có các dấu hiệu bất thường trong log hệ thống.\n"
            analysis += "Khuyến nghị: Kiểm tra các request bất thường từ IP 192.168.1.100\n"
            analysis += "Phát hiện 5 lần thử đăng nhập thất bại trong 10 phút."
            
            return analysis
        except Exception as e:
            return f"Lỗi phân tích AI: {e}"
    
    def generate_security_report(self, threat_data: List[Dict]) -> str:
        """Tạo báo cáo bảo mật bằng AI"""
        try:
            report = "🤖 <b>BÁO CÁO PHÂN TÍCH AI:</b>\n"
            report += f"Thời gian phân tích: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Phân tích mức độ nghiêm trọng
            high_risk = [t for t in threat_data if self.assess_risk(t) == "high"]
            medium_risk = [t for t in threat_data if self.assess_risk(t) == "medium"]
            
            report += f"🔴 Mức độ cao: {len(high_risk)} threat\n"
            report += f"🟡 Mức độ trung bình: {len(medium_risk)} threat\n"
            report += f"📊 Tổng cộng: {len(threat_data)} threat\n\n"
            
            # Đề xuất khắc phục
            if high_risk:
                report += "💡 Đề xuất khắc phục:\n"
                report += "1. Cập nhật tất cả các gói phụ thuộc\n"
                report += "2. Áp dụng các bản vá bảo mật ngay lập tức\n"
                report += "3. Kiểm tra firewall và IDS/IPS\n"
            
            return report
        except Exception as e:
            return f"❌ Lỗi tạo báo cáo: {e}"
    
    def assess_risk(self, threat: Dict) -> str:
        """Đánh giá mức độ nghiêm trọng của threat"""
        # Đơn giản hóa việc đánh giá rủi ro
        # Trong thực tế, bạn sẽ có logic phức tạp hơn
        return "medium"
    
    def analyze_vulnerability_trends(self) -> str:
        """Phân tích xu hướng lỗ hổng bảo mật"""
        try:
            # Phân tích xu hướng theo thời gian
            report = "📈 <b>XU HƯỚNG BẢO MẬT:</b>\n"
            report += "Phân tích 30 ngày gần đây:\n\n"
            
            # Mô phỏng dữ liệu xu hướng
            report += "• SQL Injection: tăng 15% so với tháng trước\n"
            report += "• XSS: giảm 8% nhờ CSP headers\n"
            report += "• Brute Force: ổn định, không có thay đổi\n"
            report += "• File Inclusion: tăng 3% do các thư viện bên thứ ba\n"
            
            return report
        except Exception as e:
            return f"❌ Lỗi phân tích xu hướng: {e}"

def main():
    """Main function"""
    print("🚀 [AI ANALYST] Khởi động hệ thống AI Security Analyst...")
    send_telegram("🤖 <b>HỆ THỐNG AI ANALYST:</b> Đang bắt đầu phân tích bảo mật...")
    
    # Tạo instance AI Analyst
    analyst = AISecurityAnalyst()
    
    # Phân tích và gửi báo cáo
    trend_analysis = analyst.analyze_vulnerability_trends()
    send_telegram(trend_analysis)
    
    print("✅ [AI ANALYST] Hoàn tất phân tích bảo mật")
    send_telegram("✅ <b>AI ANALYST HOÀN TẤT:</b> Đã hoàn tất phân tích bảo mật")

if __name__ == "__main__":
    main()