import os
import requests
from github import Github
import datetime
from dotenv import load_dotenv
load_dotenv("/home/phong/evonet-core/.env", override=True)

# --- CẤU HÌNH BIẾN ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # Sếp cần tạo trên GitHub
REPO_NAME = os.getenv("GITHUB_REPO") # Ví dụ: "phonghuynh/evonet-core"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def ask_nvidia_to_fix(error_log, file_content):
    """Giao file lỗi và log lỗi cho Nvidia NIM để nó tự viết lại code"""
    print("🧠 Gọi Kỹ sư Trưởng Nvidia phân tích lỗi...")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""
    Hệ thống vừa sập. Dưới đây là Log lỗi:
    {error_log}
    
    Và đây là nội dung file code hiện tại:
    ```python
    {file_content}
    ```
    
    Hãy tìm ra nguyên nhân và TRẢ VỀ TOÀN BỘ ĐOẠN CODE ĐÃ ĐƯỢC VÁ LỖI. 
    Lưu ý: Chỉ trả về code thuần, KHÔNG giải thích lằng nhằng, KHÔNG dùng markdown ```python, để tôi có thể ghi thẳng vào file.
    """
    
    payload = {
        "model": "nvidia/nemotron-4-340b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1 # Tránh việc AI sáng tạo quá đà làm sai logic code
    }
    
    res = requests.post(url, headers=headers, json=payload)
    return res.json()["choices"][0]["message"]["content"].strip()

def create_auto_fix_pr(file_path, error_log):
    """Tự động tạo nhánh mới và mở Pull Request trên GitHub với kiểm thử tự động"""
    # Import here to avoid circular imports
    from auto_patch_generator import create_auto_fix_pr as auto_patch_create_pr
    # Delegate to the new auto patch generator
    auto_patch_create_pr(file_path, error_log)

# Chạy test giả lập
if __name__ == "__main__":
    # Giả lập một lỗi chia cho 0 trong file main.py
    fake_error = "ZeroDivisionError: division by zero at line 42 in ask_api()"
    # Chỉ gọi hàm khi sếp đã cấu hình xong Repo
    # create_auto_fix_pr("app/main.py", fake_error)
