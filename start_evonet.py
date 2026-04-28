#!/usr/bin/env python3
"""
Evonet-core: Hệ thống AI tự học và tiến hóa bảo mật
Script tổng hợp để chạy tất cả các thành phần đã được cải thiện
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path
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

def check_docker_compose():
    """Check if docker-compose is available"""
    try:
        result = subprocess.run(["docker-compose", "--version"], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def start_docker_services():
    """Start all Docker services"""
    try:
        print("Starting Docker services...")
        send_telegram("🐳 <b>KHỞI ĐỘNG DỊCH VỤ:</b> Đang khởi động các dịch vụ Docker...")
        
        # Start services
        result = subprocess.run(["docker-compose", "up", "-d"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Docker services started successfully")
            send_telegram("✅ <b>DỊCH VỤ ĐÃ SẴN SÀNG:</b> Tất cả các dịch vụ đã được khởi động")
            return True
        else:
            print(f"Error starting Docker services: {result.stderr}")
            send_telegram(f"❌ <b>LỖI DỊCH VỤ:</b> Không thể khởi động các dịch vụ Docker\n{result.stderr}")
            return False
    except Exception as e:
        print(f"Error starting Docker services: {e}")
        send_telegram(f"❌ <b>LỖI DỊCH VỤ:</b> Lỗi khi khởi động các dịch vụ Docker: {e}")
        return False

def check_api_health():
    """Check if the main API is healthy"""
    try:
        response = requests.get("http://localhost:8080/v1/models", timeout=10)
        return response.status_code == 200
    except:
        return False

def check_dashboard_health():
    """Check if the dashboard is healthy"""
    try:
        response = requests.get("http://localhost:8081", timeout=10)
        return response.status_code == 200
    except:
        return False

def run_initial_setup():
    """Run initial setup tasks"""
    try:
        print("Running initial setup...")
        send_telegram("⚙️ <b>THIẾT LẬP BAN ĐẦU:</b> Đang chạy các tác vụ thiết lập ban đầu...")
        
        # Run threat collection
        print("Collecting threat intelligence...")
        send_telegram("🤖 <b>THU THẬP THÔNG TIN ĐE DỌA:</b> Đang thu thập dữ liệu từ các nguồn đe dọa...")
        subprocess.run(["python", "app/scripts/threat_intel_collector.py"], 
                      capture_output=True, text=True, timeout=300)
        
        # Run CVE collection
        print("Collecting CVEs...")
        send_telegram("👁️ <b>THU THẬP CVE:</b> Đang rà quét và nạp lỗ hổng CVE từ NVD...")
        subprocess.run(["python", "app/scripts/cve_refinery.py"], 
                      capture_output=True, text=True, timeout=300)
        
        # Run self evolution
        print("Running self evolution...")
        send_telegram("🧠 <b>TỰ HỌC & TIẾN HÓA:</b> Đang phân tích lỗ hổng và tự viết tuyệt chiêu phòng thủ...")
        subprocess.run(["python", "app/scripts/self_evolve.py"], 
                      capture_output=True, text=True, timeout=600)
        
        send_telegram("✅ <b>THIẾT LẬP BAN ĐẦU HOÀN TẤT:</b> Hệ thống đã sẵn sàng để hoạt động")
        return True
    except Exception as e:
        print(f"Error in initial setup: {e}")
        send_telegram(f"❌ <b>THIẾT LẬP BAN ĐẦU THẤT BẠI:</b> {e}")
        return False

def start_auto_update_system():
    """Start the auto update system"""
    try:
        print("Starting auto update system...")
        send_telegram("🔄 <b>HỆ THỐNG TỰ ĐỘNG:</b> Đang khởi động chế độ tự động hoàn toàn...")
        
        # Start auto update system in background
        subprocess.Popen(["python", "app/scripts/auto_update_system.py"])
        
        return True
    except Exception as e:
        print(f"Error starting auto update system: {e}")
        send_telegram(f"❌ <b>LỖI HỆ THỐNG TỰ ĐỘNG:</b> {e}")
        return False

def main():
    """Main function to start the complete system"""
    print("Starting Evonet-core complete system...")
    send_telegram("🚀 <b>EVONET-CORE:</b> Đang khởi động hệ thống AI tự học và tiến hóa bảo mật...")
    
    # Check Docker availability
    if not check_docker_compose():
        print("Docker-compose not available, please install Docker")
        send_telegram("⚠️ <b>YÊU CẦU HỆ THỐNG:</b> Vui lòng cài đặt Docker và Docker-compose")
        return
    
    # Start Docker services
    if not start_docker_services():
        print("Failed to start Docker services")
        return
    
    # Wait for services to be ready
    print("Waiting for services to be ready...")
    time.sleep(30)
    
    # Check API health
    if not check_api_health():
        print("Main API is not healthy")
        send_telegram("⚠️ <b>API KHÔNG PHẢN HỒI:</b> API chính không phản hồi, vui lòng kiểm tra lại")
        return
    
    # Check dashboard health
    if not check_dashboard_health():
        print("Dashboard is not healthy")
        send_telegram("⚠️ <b>DASHBOARD KHÔNG PHẢN HỒI:</b> Dashboard không phản hồi, vui lòng kiểm tra lại")
        return
    
    # Run initial setup
    if not run_initial_setup():
        print("Initial setup failed")
        return
    
    # Start auto update system
    if not start_auto_update_system():
        print("Failed to start auto update system")
        return
    
    # System is ready
    print("Evonet-core system is ready!")
    send_telegram("✅ <b>EVONET-CORE SẴN SÀNG:</b> Hệ thống AI tự học và tiến hóa bảo mật đã sẵn sàng hoạt động")
    send_telegram("🌐 <b>GIAO DIỆN WEB:</b> Truy cập http://localhost:8081 để xem dashboard")
    send_telegram("📱 <b>ĐIỀU KHIỂN:</b> Sử dụng Telegram bot để điều khiển hệ thống")
    
    print("System is running. Press Ctrl+C to stop.")
    
    # Keep the script running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down...")
        send_telegram("🔴 <b>EVONET-CORE ĐANG TẮT:</b> Hệ thống đang được tắt...")
        subprocess.run(["docker-compose", "down"])
        print("System shut down.")

if __name__ == "__main__":
    main()