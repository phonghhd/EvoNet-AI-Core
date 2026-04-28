import os
import requests
from pinecone.pinecone import Pinecone
import subprocess
from dotenv import load_dotenv
import re
import sys
import traceback
load_dotenv("/home/phong/evonet-core/.env", override=True)

# --- CẤU HÌNH ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WORKSPACE_DIR = "/workspace"

# 🛡️ Màng lọc Tử thần (Regex Blacklist Guardrail)
def regex_blacklist_guardrail(code_to_check):
    """Kiểm tra code trước khi thực thi để chặn các từ khóa cấm kỵ"""
    # Danh sách các từ khóa cấm kỵ
    blacklisted_patterns = [
        r"os\.remove",
        r"shutil\.rmtree",
        r"subprocess\.run",
        r"subprocess\.Popen",
        r"DROP TABLE",
        r"DELETE FROM",
        r"rm -rf",
        r"format.*\(",
        r"eval\s*\(",
        r"exec\s*\(",
    ]
    
    # Kiểm tra xem có chứa từ khóa cấm không
    for pattern in blacklisted_patterns:
        if re.search(pattern, code_to_check):
            # Báo động đỏ về Telegram và chặn đứng tiến trình
            error_msg = f"🚨 <b>MÀNG LỌC TỬ THẦN ĐÃ CHẶN:</b>\nPhát hiện từ khóa nguy hiểm: <code>{pattern}</code>"
            send_telegram(error_msg)
            raise Exception(f"Blocked dangerous pattern: {pattern}")
    
    return True

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def check_vulnerable_files():
    """Kiểm tra các file trong workspace có chứa lỗ hổng bảo mật"""
    vulnerable_patterns = [
        r"f\s*=\s*['\"].*{.*}.*['\"]",  # SQL Injection pattern
        r"eval\s*$",  # eval() function
        r"exec\s*$",  # exec() function
        r"os\.system\s*$",  # os.system() function
        r"subprocess\.",  # subprocess usage
    ]
    
    vulnerable_files = []
    
    # Duyệt qua tất cả các file trong workspace
    for root, dirs, files in os.walk(WORKSPACE_DIR):
        for file in files:
            if file.endswith(('.py', '.js', '.ts')):  # Chỉ kiểm tra các file code
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Kiểm tra xem file có chứa pattern nguy hiểm không
                    for pattern in vulnerable_patterns:
                        if re.search(pattern, content):
                            vulnerable_files.append(file_path)
                            break
                except Exception as e:
                    print(f"Lỗi khi đọc file {file_path}: {e}")
    
    return vulnerable_files

def check_system():
    print("🔍 Đang quét hệ thống hàng giờ...")
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        memory_index = pc.Index("evonet-memory")
        
        # Lấy bảng thống kê từ Cloud
        stats = memory_index.describe_index_stats()
        namespaces = stats.get("namespaces", {})
        
        # Đếm số lượng trong từng ngăn tủ (nếu chưa có thì mặc định là 0)
        total_cve = namespaces.get("security_knowledge_clean", {}).get("vector_count", 0)
        total_skills = namespaces.get("learned_skills", {}).get("vector_count", 0)        
        if total_cve > total_skills:
            diff = total_cve - total_skills
            send_telegram(f"📢 <b>WATCHDOG:</b> Phát hiện {diff} lỗ hổng mới chưa được học. Đang kích hoạt tiến hóa tự động...")
            subprocess.Popen(["python", "scripts/self_evolve.py"])
        
        # 2. Kiểm tra log lỗi (nếu có file error.log)
        if os.path.exists("logs/error.log") and os.path.getsize("logs/error.log") > 0:
            send_telegram("🚨 <b>WATCHDOG:</b> Phát hiện log lỗi mới! Đang gọi Evo-AutoFix để vá code...")
            subprocess.Popen(["python", "scripts/evo_autofix.py"])
            
        # 3. Kiểm tra file chứa lỗ hổng trong workspace
        vulnerable_files = check_vulnerable_files()
        if vulnerable_files:
            file_list = "\n".join(vulnerable_files)
            send_telegram(f"🚨 <b>WATCHDOG:</b> Phát hiện {len(vulnerable_files)} file chứa lỗ hổng bảo mật!\nCác file:\n{file_list}\nĐang gọi Evo-AutoFix để vá code...")
            subprocess.Popen(["python", "scripts/evo_autofix.py"])

    except Exception as e:
        error_msg = f"❌ <b>LỖI HỆ THỐNG:</b>\n{str(e)}\n{traceback.format_exc()}"
        send_telegram(error_msg)
        print(f"Lỗi Watchdog: {e}")

if __name__ == "__main__":
    check_system()
