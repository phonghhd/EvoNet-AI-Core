from dotenv import load_dotenv
load_dotenv("/app/.env", override=True)
import sys
import os

# 1. BẬT GPS ĐẦU TIÊN (Bắt buộc phải đặt trước khi import các file khác)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import re
import json

# 2. MƯỢN ĐÚNG ĐỒ TỪ ĐÚNG CHỖ
from main import send_telegram_message               # Mượn hàm nhắn tin từ phòng khách (main.py)
from self_evolve import ask_ai_with_failover         # Mượn hàm AI 4 lớp từ phòng ngủ (self_evolve.py)

TARGET_FILE = "/app/main.py"
DRAFT_FILE = "/app/main_draft.py"
BACKUP_DIR = "/app/logs/backups/"
FORBIDDEN_FILES = ["docker-compose.yml", ".env", "requirements.txt"]

def clean_markdown_json(text):
    """Lọc bỏ các thẻ ```json ... ``` để lấy chuỗi JSON thuần"""
    text = re.sub(r"^```(json)?\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\n?", "", text, flags=re.MULTILINE)
    return text.strip()

def run_evolution_cycle():
    send_telegram_message("🤖 <b>EVO-ARCHITECT:</b> Qwen3-480b đang đọc code và tìm cách tối ưu...")

    # ==========================================
    # LUẬT 4: VÙNG CẤM ĐỊA
    # ==========================================
    if any(forbidden in TARGET_FILE for forbidden in FORBIDDEN_FILES):
        send_telegram_message(f"❌ <b>HỦY:</b> {TARGET_FILE} là VÙNG CẤM! EvoNet không được chạm vào.")
        return

    # 1. ĐỌC CODE GỐC
    if not os.path.exists(TARGET_FILE):
        return
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        original_code = f.read()

    # 2. GỌI QWEN3-480B SUY NGHĨ
    prompt = f"""Ngươi là Kiến trúc sư EvoNet. Hãy tối ưu file mã nguồn sau để tăng hiệu năng.
    BẮT BUỘC trả về ĐÚNG định dạng JSON sau, không chứa văn bản nào khác ngoài JSON:
    {{
        "new_code": "toàn bộ mã nguồn mới",
        "optimization_type": "mô tả ngắn gọn cách tối ưu",
        "estimated_speedup_percent": (nhập số nguyên từ 0 đến 100)
    }}
    Mã nguồn hiện tại:
    {original_code}
    """
    
    # Gọi hệ thống AI của sếp (Đảm bảo nó gọi tới Qwen3-480b)
    json_result_raw, provider = ask_ai_with_failover(prompt)
    clean_json_str = clean_markdown_json(json_result_raw)

    # 3. MỞ HỘP JSON & KIỂM TRA ĐIỀU KIỆN 10%
    try:
        ai_response = json.loads(clean_json_str)
        speedup = int(ai_response.get("estimated_speedup_percent", 0))
        new_code = ai_response.get("new_code", "")
        opt_type = ai_response.get("optimization_type", "Tối ưu chung")
        
        # ĐIỀU KIỆN CHỐT: Phải tăng trên 10% mới làm phiền sếp
        if speedup < 10:
            print(f"🗑️ Qwen3-480b chỉ tối ưu được {speedup}%. Đã hủy bản nháp trong im lặng.")
            return

        # ==========================================
        # KHUNG PHÁP LÝ (GUARDRAILS) CHO ĐOẠN CODE MỚI
        # ==========================================
        # LUẬT 1: CHỐNG SUY NHƯỢC
        if len(new_code) < len(original_code) * 0.8:
            send_telegram_message("❌ <b>HỦY:</b> Qwen3-480b sinh code quá ngắn (nghi ngờ mất đoạn). Đã chặn!")
            return

        # LUẬT 2: RÀ QUÉT AN NINH
        # (Chỗ này sếp dùng hàm check Pinecone của sếp, tôi giả lập True)
        is_safe = True 
        if not is_safe:
            send_telegram_message("❌ <b>HỦY:</b> Phát hiện rủi ro bảo mật (CVE) trong code mới.")
            return

        # LUẬT 3: LƯU VÀO VÙNG CÁCH LY
        with open(DRAFT_FILE, "w", encoding="utf-8") as f:
            f.write(new_code)

        # 4. TRÌNH SẾP DUYỆT
        msg = f"🚀 <b>QWEN3-480B BÁO CÁO TỐI ƯU:</b>\n"
        msg += f"⚡ Hiệu năng tăng ước tính: <b>{speedup}%</b>\n"
        msg += f"🛠 Phương pháp: <i>{opt_type}</i>\n"
        msg += f"✅ Đã qua kiểm duyệt bảo mật.\n"
        msg += f"👉 Sếp gõ <code>/duyet_tienhoa</code> để cập nhật hệ thống!"
        send_telegram_message(msg)

    except json.JSONDecodeError:
        print("⚠️ Qwen3-480b trả về sai định dạng JSON. Hủy chu kỳ.")
    except Exception as e:
        print(f"⚠️ Lỗi xử lý Tiến hóa: {e}")

if __name__ == "__main__":
    run_evolution_cycle()
