import time
import subprocess
import requests
import os
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
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

def run_script(script_name):
    """Run a script and handle errors"""
    print(f"🚀 [AUTONOMOUS] Kích hoạt: {script_name}")
    try:
        # Run script as a separate process
        result = subprocess.run(["python3", f"app/scripts/{script_name}"], 
                            capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ [AUTONOMOUS] Hoàn tất: {script_name}")
            return True
        else:
            print(f"❌ [AUTONOMOUS] Lỗi khi chạy {script_name}: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ [AUTONOMOUS] Timeout khi chạy {script_name}")
        return False
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi khi chạy {script_name}: {e}")
        return False

def health_check():
    """Check system health and send status to Telegram"""
    try:
        # Check if main API is responsive
        response = requests.get("http://localhost:8080/v1/models", timeout=10)
        if response.status_code == 200:
            status = "✅ Hệ thống hoạt động bình thường"
        else:
            status = "⚠️ Hệ thống có thể gặp sự cố"
        
        # Send health status to Telegram
        send_telegram(f"🏥 <b>TÌNH TRẠNG HỆ THỐNG:</b>\n{status}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        send_telegram(f"❌ <b>LỖI HỆ THỐNG:</b>\n{e}")
        return False

def run_comprehensive_update():
    """Run comprehensive system update"""
    print("🔄 [AUTONOMOUS] Bắt đầu cập nhật toàn diện...")
    send_telegram("🔄 <b>CẬP NHẬT TOÀN DIỆN:</b> Đang bắt đầu chu trình cập nhật...")
    
    # Run threat collection
    run_script("threat_intel_collector.py")
    
    # Run CVE collection
    run_script("cve_refinery.py")
    
    # Run self evolution
    run_script("self_evolve.py")
    
    # Run auto fix
    run_script("evo_autofix.py")
    
    # Run advanced analysis
    run_script("advanced_static_analyzer.py")
    
    # Run attack simulation
    run_script("attack_simulator.py")
    
    # Run threat alert system
    run_script("threat_alert_system.py")
    
    send_telegram("✅ <b>CẬP NHẬT TOÀN DIỆN HOÀN TẤT:</b> Hệ thống đã được cập nhật toàn diện")

def autonomous_system_monitor():
    """Monitor system resources and performance"""
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check if system is under stress
        if cpu_percent > 80 or memory.percent > 80 or (disk.percent > 90):
            status = f"⚠️ Cảnh báo tài nguyên:\n"
            if cpu_percent > 80:
                status += f"CPU: {cpu_percent}%\n"
            if memory.percent > 80:
                status += f"RAM: {memory.percent}%\n"
            if disk.percent > 90:
                status += f"Disk: {disk.percent}%"
            
            send_telegram(f"⚠️ <b>CẢNH BÁO TÀI NGUYÊN:</b>\n{status}")
    except ImportError:
        print("psutil not installed, skipping system monitoring")
    except Exception as e:
        print(f"❌ System monitoring failed: {e}")

def run_federated_learning():
    """Run federated learning update"""
    try:
        from federated_learning.fl_integration import periodic_fl_training
        print("🔄 [AUTONOMOUS] Bắt đầu huấn luyện Federated Learning...")
        periodic_fl_training()
        print("✅ [AUTONOMOUS] Hoàn tất huấn luyện Federated Learning")
        return True
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi Federated Learning: {e}")
        return False

def run_continuous_learning():
    """Run continuous learning process"""
    try:
        # Run self QA for continuous learning
        run_script("self_qa.py")
        
        # Run code harvester to collect new code
        run_script("code_harvester.py")
        
        # Run system watchdog
        run_script("system_watchdog.py")
        
        return True
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi học liên tục: {e}")
        return False

def run_security_assessment():
    """Chạy đánh giá bảo mật toàn diện"""
    try:
        print("🔍 [AUTONOMOUS] Đang chạy đánh giá bảo mật...")
        send_telegram("🔍 <b>ĐÁNH GIÁ BẢO MẬT:</b> Đang bắt đầu đánh giá bảo mật toàn diện...")
        
        # Run vulnerability scanner
        run_script("vulnerability_scanner.py")
        
        # Run threat intelligence collection
        run_script("threat_intelligence.py")
        
        # Run red team simulation
        run_script("red_team_simulator.py")
        
        send_telegram("✅ <b>ĐÁNH GIÁ BẢO MẬT HOÀN TẤT:</b> Đã hoàn tất đánh giá bảo mật")
        return True
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi đánh giá bảo mật: {e}")
        send_telegram(f"❌ <b>LỖI ĐÁNH GIÁ BẢO MẬT:</b>\n{e}")
        return False

def run_bug_bounty_hunting():
    """Chạy săn bug bounty tự động"""
    try:
        print("🐛 [AUTONOMOUS] Đang chạy săn bug bounty...")
        send_telegram("🐛 <b>SĂN BUG BOUNTY:</b> Đang bắt đầu săn bug bounty tự động...")
        
        # Chạy hệ thống bug bounty hunter
        run_script("bug_bounty_hunter.py")
        
        send_telegram("✅ <b>SĂN BUG BOUNTY HOÀN TẤT:</b> Đã hoàn tất quá trình săn bug bounty")
        return True
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi săn bug bounty: {e}")
        return False

def run_incident_response():
    """Chạy phản ứng sự cố tự động"""
    try:
        print("🚨 [AUTONOMOUS] Đang chạy phản ứng sự cố...")
        send_telegram("🚨 <b>PHẢN ỨNG SỰ CỐ:</b> Đang bắt đầu phản ứng sự cố tự động...")
        
        # Chạy hệ thống incident response
        run_script("incident_response.py")
        
        send_telegram("✅ <b>PHẢN ỨNG SỰ CỐ HOÀN TẤT:</b> Đã hoàn tất phản ứng sự cố")
        return True
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi phản ứng sự cố: {e}")
        return False

def run_bug_bounty_hunting():
    """Chạy săn bug bounty tự động"""
    try:
        print("🐛 [AUTONOMOUS] Đang chạy săn bug bounty...")
        send_telegram("🐛 <b>SĂN BUG BOUNTY:</b> Đang bắt đầu săn bug bounty tự động...")
        
        # Chạy hệ thống bug bounty hunter
        run_script("bug_bounty_hunter.py")
        
        send_telegram("✅ <b>SĂN BUG BOUNTY HOÀN TẤT:</b> Đã hoàn tất quá trình săn bug bounty")
        return True
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi săn bug bounty: {e}")
        return False

def main():
    """Main autonomous manager function"""
    # Configure scheduler
    jobstores = {
        'default': MemoryJobStore()
    }
    
    executors = {
        'default': ThreadPoolExecutor(20),
    }
    
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    
    scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)
    
    # --- THIẾT LẬP VÒNG LẶP TIẾN HÓA LIÊN TỤC 24/7 ---
    
    # 1. Mỗi 30 phút: Kiểm tra sức khỏe hệ thống
    scheduler.add_job(health_check, 'interval', minutes=30, id='health_check')
    
    # 2. Mỗi 1 tiếng: Mắt thần đi quét lỗ hổng CVE mới
    scheduler.add_job(lambda: run_script("cve_refinery.py"), 'interval', hours=1, id='cve_scan')
    
    # 3. Mỗi 2 tiếng: Watchdog quét hệ thống và kích hoạt vá lỗi/tự học
    scheduler.add_job(lambda: run_script("system_watchdog.py"), 'interval', hours=2, id='system_watchdog')
    
    # 4. Mỗi 3 tiếng: Cánh tay Robot gom code nội bộ (nếu sếp có cập nhật code mới)
    scheduler.add_job(lambda: run_script("code_harvester.py"), 'interval', hours=3, id='code_harvest')
    
    # 5. Mỗi 4 tiếng: Tự động thu thập thông tin đe dọa
    scheduler.add_job(lambda: run_script("threat_intel_collector.py"), 'interval', hours=4, id='threat_collection')
    
    # 6. Mỗi 6 tiếng: Tự học & tiến hóa
    scheduler.add_job(lambda: run_script("self_evolve.py"), 'interval', hours=6, id='self_evolve')
    
    # 7. Mỗi 8 tiếng: Phân tích mã nguồn nâng cao
    scheduler.add_job(lambda: run_script("advanced_static_analyzer.py"), 'interval', hours=8, id='advanced_analysis')
    
    # 8. Mỗi 12 tiếng: Cập nhật toàn diện hệ thống
    scheduler.add_job(run_comprehensive_update, 'interval', hours=12, id='comprehensive_update')
    
    # 9. Mỗi ngày: Huấn luyện Federated Learning
    scheduler.add_job(run_federated_learning, 'interval', days=1, id='federated_learning')
    
    # 10. Mỗi 30 phút: Giám sát tài nguyên hệ thống
    scheduler.add_job(autonomous_system_monitor, 'interval', minutes=30, id='system_monitor')
    
    # 11. Mỗi 5 tiếng: Học liên tục
    scheduler.add_job(run_continuous_learning, 'interval', hours=5, id='continuous_learning')
    
    # 12. Mỗi 6 tiếng: Đánh giá bảo mật toàn diện
    scheduler.add_job(run_security_assessment, 'interval', hours=6, id='security_assessment')
    
    # 13. Mỗi ngày: Phản ứng sự cố tự động
    scheduler.add_job(run_incident_response, 'interval', days=1, id='incident_response')
    
    # 14. Mỗi 3 ngày: Săn bug bounty tự động
    scheduler.add_job(run_bug_bounty_hunting, 'interval', days=3, id='bug_bounty_hunting')
    
    # 15. Mỗi tuần: Chạy hệ thống AI analyst
    scheduler.add_job(lambda: run_script("ai_security_analyst.py"), 'interval', days=7, id='ai_security_analysis')
    
    print("🤖 EvoNet Autonomous Manager đã sẵn sàng. Bắt đầu vòng lặp tiến hóa 24/7...")
    send_telegram("🟢 <b>HỆ THỐNG TỰ ĐỘNG HOẠT ĐỘNG 24/7:</b> Đã bắt đầu vòng lặp tiến hóa liên tục")
    
    scheduler.start()
    
    try:
        # Keep the script running in the background
        while True:
            time.sleep(60)  # Check every minute
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Đang tắt hệ thống tự động...")
        send_telegram("🔴 <b>HỆ THỐNG TỰ ĐỘNG ĐANG TẮT:</b> Đang dừng vòng lặp tiến hóa")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
