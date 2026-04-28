import os
import requests
import chromadb
import datetime
import re

# --- CẤU HÌNH API & FAILOVER ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

NVIDIA_MODEL = "qwen/qwen3-coder-480b-a35b-instruct"
GROQ_MODEL = "llama-3.1-70b-versatile"

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})


def ask_ai_with_failover(prompt):
    """Pháo Đài 4 Lớp: Nvidia -> Groq -> Cloudflare -> Local"""
    
    # 1. LỚP TIỀN PHƯƠNG: NVIDIA 480B (Sâu sắc nhất)
    try:
        url_nv = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers_nv = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
        res = requests.post(url_nv, headers=headers_nv, json={"model": NVIDIA_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}, timeout=60)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"], "Nvidia 480B"
    except Exception:
        print("⚠️ Nvidia sập. Chuyển sang Groq...")

        # 2. LỚP PHẢN ỨNG NHANH: GROQ (Llama 3.1 70B)
        try:
            url_g = "https://api.groq.com/openai/v1/chat/completions"
            headers_g = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            # Sếp chú ý dùng model Llama 3.1 70B cho ổn định
            res = requests.post(url_g, headers=headers_g, json={"model": "llama-3.1-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}, timeout=25)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"], "Groq 70B"
        except Exception:
            print("⚠️ Groq sập. Kích hoạt lớp dự phòng Cloudflare...")

            # 3. LỚP DỰ PHÒNG CHIẾN LƯỢC: CLOUDFLARE WORKERS AI
            try:
                # Tận dụng Token Cloudflare sếp đã cấu hình
                cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
                cf_token = os.getenv("CLOUDFLARE_API_KEY")
                url_cf = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/meta/llama-3.1-70b-instruct"
                headers_cf = {"Authorization": f"Bearer {cf_token}"}
                res = requests.post(url_cf, headers=headers_cf, json={"messages": [{"role": "user", "content": prompt}]}, timeout=20)
                res.raise_for_status()
                return res.json()["result"]["response"], "Cloudflare AI (70B)"
            except Exception:
                print("⚠️ Cả 3 lớp Cloud đều chết! Chốt chặn cuối cùng: Local AI...")

                # 4. CHỐT CHẶN CUỐI CÙNG: LOCAL AI (OLLAMA)
                try:
                    url_l = "http://host.docker.internal:11434/v1/chat/completions"
                    res = requests.post(url_l, json={"model": "qwen2.5-coder:32b", "messages": [{"role": "user", "content": prompt}]}, timeout=15)
                    res.raise_for_status()
                    return res.json()["choices"][0]["message"]["content"], "Local AI (Nội bộ)"
                except Exception:
                    raise Exception("Sập toàn tập 4 lớp! Vui lòng kiểm tra lại kết nối mạng hoặc Local AI.")

def generate_qa():
    send_telegram("🌌 <b>TRẠNG THÁI NGỦ SÂU:</b> AI đang tự tưởng tượng ra các kịch bản tấn công mạng để luyện tập...")
    
    try:
        chroma_client = chromadb.HttpClient(host='evonet_vector_db', port=8000)
        skills_collection = chroma_client.get_or_create_collection(name="learned_skills")

        # Ép AI tự biên tự diễn
        prompt = """
        Bạn là một Chuyên gia An ninh Mạng và Kiến trúc sư Phần mềm.
        Hãy TỰ ĐẶT RA một tình huống lỗi bảo mật web phức tạp (hoặc một bài toán tối ưu code), 
        sau đó TỰ TRẢ LỜI bằng cách viết đoạn code Python/Node.js để giải quyết nó.
        
        Định dạng mong muốn:
        - Tình huống giả định: [Mô tả ngắn gọn]
        - Cách giải quyết: [Phân tích]
        - Code mẫu: [Code thực tế]
        BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT.
        """

        qa_content, used_model = ask_ai_with_failover(prompt)

        # Lưu giấc mơ vào não
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_id = f"dream_qa_{timestamp}"
        
        skills_collection.add(
            documents=[qa_content],
            metadatas=[{"source": "self_generated_dream", "type": "qa_simulation", "model": used_model}],
            ids=[doc_id]
        )

        preview = qa_content[:300].replace('<', '&lt;').replace('>', '&gt;')
        msg = f"💡 <b>TỰ SÁNG TẠO THÀNH CÔNG!</b>\n⚙️ <i>Tác giả: {used_model}</i>\n\nEm vừa nghĩ ra một kịch bản mới và đã lưu vào não bộ.\n\n<b>Trích lục:</b>\n<i>{preview}...</i>"
        send_telegram(msg)
        print("Tự đẻ bài thành công!")

    except Exception as e:
        send_telegram(f"❌ <b>Lỗi khi tự mơ:</b> {e}")

if __name__ == "__main__":
    generate_qa()
