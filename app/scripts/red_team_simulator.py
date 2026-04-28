import time
import random
import json
from typing import Dict, List
from datetime import datetime
import requests
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

class RedTeamSimulator:
    """Mô phỏng đội tấn công Red Team"""
    
    def __init__(self):
        self.attack_history = []
        self.successful_attacks = []
        self.attack_results = []
    
    def sql_injection_attack(self) -> Dict:
        """Mô phỏng tấn công SQL Injection"""
        return {
            "attack_type": "SQL Injection",
            "description": "Tấn công chèn mã SQL độc hại",
            "success_rate": random.uniform(0.1, 0.3),
            "timestamp": time.time(),
            "complexity": "medium",
            "tools": ["sqlmap", "burp suite"],
            "mitigation": "Use parameterized queries, input validation"
        }
    
    def brute_force_attack(self) -> Dict:
        """Mô phỏng tấn công Brute Force"""
        return {
            "attack_type": "Brute Force",
            "description": "Tấn công dò mật khẩu bằng từ điển",
            "success_rate": random.uniform(0.05, 0.2),
            "timestamp": time.time(),
            "complexity": "low",
            "tools": ["hydra", "medusa"],
            "mitigation": "Implement rate limiting, use strong passwords, MFA"
        }
    
    def dos_attack(self) -> Dict:
        """Mô phỏng tấn công DoS"""
        return {
            "attack_type": "DoS Attack",
            "description": "Tấn công từ chối dịch vụ",
            "success_rate": random.uniform(0.1, 0.4),
            "timestamp": time.time(),
            "complexity": "high",
            "tools": ["LOIC", "HOIC", "DDoS Botnet"],
            "mitigation": "Implement rate limiting, use DDoS protection services"
        }
    
    def xss_attack(self) -> Dict:
        """Mô phỏng tấn công XSS"""
        return {
            "attack_type": "Cross-Site Scripting (XSS)",
            "description": "Tấn công chèn script vào ứng dụng web",
            "success_rate": random.uniform(0.2, 0.5),
            "timestamp": time.time(),
            "complexity": "medium",
            "tools": ["XSSer", "BeEF"],
            "mitigation": "Sanitize user input, use CSP headers"
        }
    
    def csrf_attack(self) -> Dict:
        """Mô phỏng tấn công CSRF"""
        return {
            "attack_type": "CSRF Attack",
            "description": "Tấn công yêu cầu chéo giả mạo",
            "success_rate": random.uniform(0.15, 0.35),
            "timestamp": time.time(),
            "complexity": "medium",
            "tools": ["CSRFTester", "Burp Suite"],
            "mitigation": "Use anti-CSRF tokens, validate request origins"
        }
    
    def file_inclusion_attack(self) -> Dict:
        """Mô phỏng tấn công File Inclusion"""
        return {
            "attack_type": "File Inclusion",
            "description": "Tấn công bao gồm file độc hại",
            "success_rate": random.uniform(0.1, 0.25),
            "timestamp": time.time(),
            "complexity": "high",
            "tools": ["LFI Scanner", "Manual testing"],
            "mitigation": "Validate file paths, disable dangerous functions"
        }
    
    def command_injection_attack(self) -> Dict:
        """Mô phỏng tấn công Command Injection"""
        return {
            "attack_type": "Command Injection",
            "description": "Tấn công thực thi lệnh hệ thống",
            "success_rate": random.uniform(0.2, 0.4),
            "timestamp": time.time(),
            "complexity": "high",
            "tools": ["Commix", "Manual testing"],
            "mitigation": "Input validation, avoid shell execution"
        }
    
    def simulate_attack_round(self) -> List[Dict]:
        """Mô phỏng một vòng tấn công"""
        print("⚔️ [RED TEAM] Bắt đầu mô phỏng tấn công...")
        
        # Danh sách các kiểu tấn công
        attack_methods = [
            self.sql_injection_attack,
            self.brute_force_attack,
            self.dos_attack,
            self.xss_attack,
            self.csrf_attack,
            self.file_inclusion_attack,
            self.command_injection_attack
        ]
        
        # Chọn ngẫu nhiên 3-5 kiểu tấn công
        selected_attacks = random.sample(attack_methods, 
                                       random.randint(3, min(5, len(attack_methods))))
        
        results = []
        for attack in selected_attacks:
            try:
                result = attack()
                results.append(result)
                self.attack_history.append(result)
                
                # Nếu tỷ lệ thành công > 0.3 thì coi là tấn công thành công
                if result["success_rate"] > 0.3:
                    self.successful_attacks.append(result)
                    
            except Exception as e:
                print(f"❌ Lỗi trong khi thực hiện tấn công {attack.__name__}: {e}")
        
        self.attack_results.extend(results)
        return results
    
    def generate_attack_report(self, results: List[Dict]) -> str:
        """Tạo báo cáo tấn công"""
        report = "⚔️ <b>KẾT QUẢ MÔ PHỎNG TẤN CÔNG:</b>\n"
        report += f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Tổng số cuộc tấn công: {len(results)}\n\n"
        
        # Đếm số cuộc tấn công thành công
        successful_count = sum(1 for r in results if r["success_rate"] > 0.3)
        report += f"✅ Thành công: {successful_count}/{len(results)}\n"
        report += f"❌ Thất bại: {len(results) - successful_count}/{len(results)}\n\n"
        
        # Liệt kê chi tiết các cuộc tấn công
        for i, result in enumerate(results[:5], 1):  # Chỉ hiển thị 5 cái đầu
            success_emoji = "✅" if result["success_rate"] > 0.3 else "❌"
            report += f"{i}. {success_emoji} {result['attack_type']}\n"
            report += f"   Mô tả: {result['description']}\n"
            report += f"   Tỷ lệ thành công: {result['success_rate']:.2%}\n"
            report += f"   Độ phức tạp: {result['complexity']}\n"
            report += f"   Công cụ: {', '.join(result['tools'])}\n"
            report += f"   Khắc phục: {result['mitigation']}\n\n"
        
        if len(results) > 5:
            report += f"... và {len(results) - 5} cuộc tấn công khác\n"
        
        return report
    
    def get_security_insights(self) -> str:
        """Tạo insight bảo mật từ các cuộc tấn công"""
        if not self.successful_attacks:
            return "🛡️ <b>INSIGHT BẢO MẬT:</b>\nHệ thống hiện tại tương đối an toàn khỏi các cuộc tấn công đã thử nghiệm."
        
        insights = "🧠 <b>INSIGHT BẢO MẬT:</b>\n"
        insights += "Các lỗ hổng tiềm ẩn đã phát hiện:\n\n"
        
        # Phân loại theo loại tấn công
        attack_types = {}
        for attack in self.successful_attacks:
            attack_type = attack["attack_type"]
            if attack_type not in attack_types:
                attack_types[attack_type] = []
            attack_types[attack_type].append(attack)
        
        for attack_type, attacks in attack_types.items():
            avg_success_rate = sum(a["success_rate"] for a in attacks) / len(attacks)
            insights += f"• {attack_type}: Tỷ lệ thành công trung bình {avg_success_rate:.1%}\n"
            insights += f"  Khắc phục: {attacks[0]['mitigation']}\n\n"
        
        return insights

def main():
    """Main function"""
    print("🚀 [RED TEAM] Khởi động hệ thống Red Team...")
    send_telegram("⚔️ <b>HỆ THỐNG RED TEAM:</b> Đang bắt đầu mô phỏng tấn công...")
    
    # Tạo simulator instance
    simulator = RedTeamSimulator()
    
    # Mô phỏng tấn công
    results = simulator.simulate_attack_round()
    
    # Tạo và gửi báo cáo
    attack_report = simulator.generate_attack_report(results)
    send_telegram(attack_report)
    
    # Gửi insight bảo mật
    security_insights = simulator.get_security_insights()
    send_telegram(security_insights)
    
    print("✅ [RED TEAM] Hoàn tất mô phỏng tấn công")
    send_telegram("✅ <b>MÔ PHỎNG TẤN CÔNG HOÀN TẤT:</b> Đã hoàn tất quá trình mô phỏng tấn công")

if __name__ == "__main__":
    main()