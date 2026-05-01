import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str) -> bool:
    """Send a message via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "HTML"
    }
    
    try: 
        response = requests.post(url, json=payload, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def send_patch_approval_request(cve_id: str, patch_summary: str) -> bool:
    """Send a patch approval request via Telegram"""
    message = f"""🚨 <b>YÊU CẦU DUYỆT BẢN VÁ</b> 🚨

🧠 <b>Qwen</b> đã tạo bản vá cho lỗ hổng:
<b>{cve_id}</b>

📝 <b>Tóm tắt bản vá:</b>
{patch_summary}

✅ Để duyệt và áp dụng bản vá, hãy nhấn: /duyet_tienhoa
❌ Để từ chối bản vá, hãy nhấn: /tu_choi

<i>Hãy kiểm tra kỹ thông tin trước khi duyệt!</i>"""
    
    return send_telegram_message(message)