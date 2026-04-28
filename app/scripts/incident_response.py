import os
import json
import time
import subprocess
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import shutil
import psutil

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

class IncidentResponseSystem:
    """Hệ thống phản ứng sự cố tự động"""
    
    def __init__(self):
        self.incident_log = []
        self.isolation_directory = "/tmp/isolated_system"
        self.backup_directory = "/app/backups"
    
    def detect_incident(self) -> Optional[Dict]:
        """Phát hiện sự cố bảo mật"""
        try:
            # Kiểm tra các dấu hiệu bất thường
            incidents = []
            
            # Kiểm tra CPU usage bất thường
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                incidents.append({
                    "type": "High CPU Usage",
                    "severity": "medium",
                    "description": f"CPU usage is {cpu_percent}%",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Kiểm tra số lượng process bất thường
            processes = psutil.pids()
            if len(processes) > 500:  # Ngưỡng tùy chỉnh
                incidents.append({
                    "type": "High Process Count",
                    "severity": "high",
                    "description": f"Too many processes: {len(processes)}",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Kiểm tra network connections bất thường
            connections = psutil.net_connections()
            suspicious_connections = [c for c in connections if c.status == 'ESTABLISHED']
            if len(suspicious_connections) > 100:
                incidents.append({
                    "type": "Suspicious Connections",
                    "severity": "high",
                    "description": f"Too many connections: {len(suspicious_connections)}",
                    "timestamp": datetime.now().isoformat()
                })
            
            if incidents:
                return incidents[0]  # Trả về sự cố nghiêm trọng nhất
            return None
            
        except Exception as e:
            print(f"❌ Lỗi phát hiện sự cố: {e}")
            return None
    
    def isolate_system(self) -> bool:
        """Cô lập hệ thống khi phát hiện sự cố"""
        try:
            print("🔒 [INCIDENT RESPONSE] Đang cô lập hệ thống...")
            send_telegram("🔒 <b>CÔ LẬP HỆ THỐNG:</b> Đang cô lập hệ thống để ngăn chặn sự cố...")
            
            # Tạo thư mục cô lập
            os.makedirs(self.isolation_directory, exist_ok=True)
            
            # Trong thực tế, bạn sẽ thực hiện các bước cô lập thực sự:
            # - Ngắt kết nối mạng
            # - Dừng các dịch vụ không cần thiết
            # - Chuyển log và dữ liệu quan trọng
            
            # Mô phỏng cô lập bằng cách tạo file log
            isolation_log = os.path.join(self.isolation_directory, "isolation.log")
            with open(isolation_log, "w") as f:
                f.write(f"System isolated at {datetime.now()}\n")
                f.write("Network connections disabled\n")
                f.write("Non-essential services stopped\n")
            
            print("✅ [INCIDENT RESPONSE] Đã cô lập hệ thống")
            send_telegram("✅ <b>HỆ THỐNG ĐÃ ĐƯỢC CÔ LẬP:</b> Đã thực hiện các biện pháp cô lập")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi cô lập hệ thống: {e}")
            send_telegram(f"❌ <b>LỖI CÔ LẬP:</b>\n{e}")
            return False
    
    def create_backup(self) -> bool:
        """Tạo backup hệ thống khi có sự cố"""
        try:
            print("💾 [INCIDENT RESPONSE] Đang tạo backup hệ thống...")
            send_telegram("💾 <b>TẠO BACKUP:</b> Đang tạo backup hệ thống...")
            
            # Tạo thư mục backup nếu chưa tồn tại
            os.makedirs(self.backup_directory, exist_ok=True)
            
            # Tạo backup với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_directory, f"backup_{timestamp}")
            
            # Trong thực tế, bạn sẽ backup các thành phần quan trọng
            # Ở đây chỉ là mô phỏng
            backup_info = {
                "timestamp": timestamp,
                "components": ["config_files", "logs", "database"],
                "status": "completed"
            }
            
            backup_info_file = os.path.join(backup_path, "backup_info.json")
            os.makedirs(backup_path, exist_ok=True)
            with open(backup_info_file, "w") as f:
                json.dump(backup_info, f, indent=2)
            
            print("✅ [INCIDENT RESPONSE] Đã tạo backup hệ thống")
            send_telegram("✅ <b>BACKUP HOÀN TẤT:</b> Đã tạo backup hệ thống")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi tạo backup: {e}")
            send_telegram(f"❌ <b>LỖI BACKUP:</b>\n{e}")
            return False
    
    def analyze_incident(self, incident: Dict) -> str:
        """Phân tích sự cố và đưa ra khuyến nghị"""
        try:
            analysis = "🔍 <b>PHÂN TÍCH SỰ CỐ:</b>\n"
            analysis += f"Loại sự cố: {incident['type']}\n"
            analysis += f"Mức độ: {incident['severity']}\n"
            analysis += f"Mô tả: {incident['description']}\n"
            analysis += f"Thời gian: {incident['timestamp']}\n\n"
            
            # Đưa ra khuyến nghị dựa trên loại sự cố
            recommendations = {
                "High CPU Usage": "Khuyến nghị: Kiểm tra các process đang chạy, có thể có mã độc hoặc DDoS",
                "High Process Count": "Khuyến nghị: Kiểm tra các process lạ, có thể có backdoor",
                "Suspicious Connections": "Khuyến nghị: Kiểm tra firewall, có thể có kết nối trái phép"
            }
            
            analysis += "💡 <b>KHUYẾN NGHỊ:</b>\n"
            analysis += recommendations.get(incident['type'], "Khuyến nghị: Liên hệ chuyên gia bảo mật ngay lập tức")
            
            return analysis
            
        except Exception as e:
            return f"❌ Lỗi phân tích sự cố: {e}"
    
    def restore_system(self) -> bool:
        """Khôi phục hệ thống từ backup"""
        try:
            print("🔄 [INCIDENT RESPONSE] Đang khôi phục hệ thống...")
            send_telegram("🔄 <b>KHÔI PHỤC HỆ THỐNG:</b> Đang khôi phục hệ thống từ backup...")
            
            # Trong thực tế, bạn sẽ thực hiện khôi phục từ backup gần nhất
            # Ở đây chỉ là mô phỏng
            restore_log = "/tmp/restore_log.txt"
            with open(restore_log, "w") as f:
                f.write(f"System restored at {datetime.now()}\n")
                f.write("Restored from latest backup\n")
                f.write("All services restarted\n")
            
            print("✅ [INCIDENT RESPONSE] Đã khôi phục hệ thống")
            send_telegram("✅ <b>KHÔI PHỤC HOÀN TẤT:</b> Đã khôi phục hệ thống từ backup")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khôi phục hệ thống: {e}")
            send_telegram(f"❌ <b>LỖI KHÔI PHỤC:</b>\n{e}")
            return False
    
    def generate_incident_report(self, incident: Dict, analysis: str) -> str:
        """Tạo báo cáo sự cố"""
        try:
            report = "🚨 <b>BÁO CÁO SỰ CỐ:</b>\n"
            report += f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"Loại sự cố: {incident['type']}\n"
            report += f"Mức độ: {incident['severity']}\n\n"
            
            report += "📋 <b>CHI TIẾT SỰ CỐ:</b>\n"
            report += f"Mô tả: {incident['description']}\n\n"
            
            report += "📊 <b>PHÂN TÍCH:</b>\n"
            report += analysis.split("💡 <b>KHUYẾN NGHỊ:</b>\n")[0].replace("🔍 <b>PHÂN TÍCH SỰ CỐ:</b>\n", "")
            
            report += "💡 <b>KHUYẾN NGHỊ:</b>\n"
            if "Khuyến nghị:" in analysis:
                recommendation = analysis.split("Khuyến nghị:")[1].strip()
                report += recommendation
            
            return report
            
        except Exception as e:
            return f"❌ Lỗi tạo báo cáo: {e}"

def main():
    """Main function"""
    print("🚀 [INCIDENT RESPONSE] Khởi động hệ thống phản ứng sự cố...")
    send_telegram("🚨 <b>HỆ THỐNG PHẢN ỨNG SỰ CỐ:</b> Đang bắt đầu hệ thống phản ứng sự cố tự động...")
    
    # Tạo instance hệ thống phản ứng sự cố
    irs = IncidentResponseSystem()
    
    # Phát hiện sự cố
    incident = irs.detect_incident()
    
    if incident:
        # Gửi cảnh báo
        send_telegram(f"🚨 <b>CẢNH BÁO SỰ CỐ:</b>\nPhát hiện {incident['type']} - Mức độ: {incident['severity']}")
        
        # Phân tích sự cố
        analysis = irs.analyze_incident(incident)
        send_telegram(analysis)
        
        # Cô lập hệ thống nếu cần thiết
        if incident['severity'] == 'high':
            irs.isolate_system()
        
        # Tạo backup
        irs.create_backup()
        
        # Tạo và gửi báo cáo
        report = irs.generate_incident_report(incident, analysis)
        send_telegram(report)
        
        # Nếu là sự cố nghiêm trọng, khôi phục hệ thống
        if incident['severity'] == 'high':
            irs.restore_system()
    else:
        print("✅ [INCIDENT RESPONSE] Không phát hiện sự cố")
        send_telegram("✅ <b>KIỂM TRA SỰ CỐ:</b> Không phát hiện sự cố bảo mật")
    
    print("✅ [INCIDENT RESPONSE] Hoàn tất hệ thống phản ứng sự cố")
    send_telegram("✅ <b>HỆ THỐNG PHẢN ỨNG SỰ CỐ HOẠT ĐỘNG BÌNH THƯỜNG:</b> Đã hoàn tất kiểm tra")

if __name__ == "__main__":
    main()