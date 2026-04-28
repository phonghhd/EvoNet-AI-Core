import os
import requests
import chromadb
import datetime
import re

# --- 1. CẤU HÌNH CẢ 2 NGUỒN SỨC MẠNH ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

NVIDIA_MODEL = "qwen/qwen3-coder-480b-a35b-instruct" # Trùm cuối (Ưu tiên 1)
GROQ_MODEL = "llama-3.1-70b-versatile"               # Bánh xe dự phòng (Ưu tiên 2)

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



def evolve():
    send_telegram("🧬 <b>BẮT ĐẦU TIẾN HÓA:</b> Đang nghiên cứu tài liệu bảo mật mới...")
    print("Khởi động vòng lặp tự học...")
    
    try:
        chroma_client = chromadb.HttpClient(host='evonet_vector_db', port=8000)
        cve_collection = chroma_client.get_or_create_collection(name="security_knowledge_clean")
        skills_collection = chroma_client.get_or_create_collection(name="learned_skills")

        results = cve_collection.peek(limit=1)

        if not results['documents']:
            print("Chưa có CVE nào trong não để học.")
            return

        cve_text = results['documents'][0]
        cve_id = results['ids'][0] if results['ids'] else "Unknown_CVE"

        print(f"Đang phân tích cách phòng thủ cho: {cve_id}")

        prompt = f"""
        Dưới đây là thông tin về một lỗ hổng bảo mật:
        {cve_text}

        Hãy:
        1. Giải thích ngắn gọn cơ chế lỗi.
        2. Viết code mẫu (Python/Node.js) để NGĂN CHẶN.
        BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT CHUYÊN NGHIỆP.
        """

        # Gọi hàm Failover
        defense_code, used_model = ask_ai_with_failover(prompt)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        skills_collection.add(
            documents=[defense_code],
            metadatas=[{"source": cve_id, "type": "defense_skill", "model_used": used_model}],
            ids=[f"skill_{cve_id}_{timestamp}"]
        )

        preview_text = defense_code[:400].replace('<', '&lt;').replace('>', '&gt;')
        # Báo cho sếp biết thằng nào vừa lập công
        msg = f"🧠 <b>TIẾN HÓA THÀNH CÔNG!</b>\n⚙️ <i>Phụ trách bởi: {used_model}</i>\n\nEm đã học xong cách chống lại <code>{cve_id}</code>.\n\n<b>Trích lục:</b>\n<i>{preview_text}...</i>"
        send_telegram(msg)
        print(f"✅ Tiến hóa thành công bằng {used_model}!")

    except Exception as e:
        error_msg = f"🚨 <b>LỖI HỆ THỐNG NGHIÊM TRỌNG:</b>\nTiến hóa thất bại. {e}"
        print(error_msg)
        send_telegram(error_msg) # Cả 2 cùng sập thì mới réo sếp

if __name__ == "__main__":
    evolve()
