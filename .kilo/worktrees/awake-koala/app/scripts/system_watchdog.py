import os
import requests
import chromadb
import subprocess

# --- CẤU HÌNH ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def check_system():
    print("🔍 Đang quét hệ thống hàng giờ...")
    try:
        chroma_client = chromadb.HttpClient(host='evonet_vector_db', port=8000)
        cve_col = chroma_client.get_or_create_collection(name="security_knowledge_clean")
        skills_col = chroma_client.get_or_create_collection(name="learned_skills")

        # 1. Kiểm tra lỗ hổng chưa xử lý
        total_cve = cve_col.count()
        total_skills = skills_col.count()
        
        if total_cve > total_skills:
            diff = total_cve - total_skills
            send_telegram(f"📢 <b>WATCHDOG:</b> Phát hiện {diff} lỗ hổng mới chưa được học. Đang kích hoạt tiến hóa tự động...")
            subprocess.Popen(["python", "scripts/self_evolve.py"])
        
        # 2. Kiểm tra log lỗi (nếu có file error.log)
        if os.path.exists("logs/error.log") and os.path.getsize("logs/error.log") > 0:
            send_telegram("🚨 <b>WATCHDOG:</b> Phát hiện log lỗi mới! Đang gọi Evo-AutoFix để vá code...")
            subprocess.Popen(["python", "scripts/evo_autofix.py"])

    except Exception as e:
        print(f"Lỗi Watchdog: {e}")

if __name__ == "__main__":
    check_system()
