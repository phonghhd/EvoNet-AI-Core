from dotenv import load_dotenv
import os
load_dotenv("/home/phong/evonet-core/.env", override=True)
import requests
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

def get_embedding(text: str):
    cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    cf_key = os.getenv("CLOUDFLARE_API_KEY")
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]})
        data = res.json()
        if data.get("success"): return data["result"]["data"][0]
        return None
    except: return None

def ask_ai_with_failover(prompt):
    """Pháo Đài 4 Lớp: Nvidia -> Groq -> Cloudflare -> Local"""
    
    # 1. LỚP TIỀN PHƯƠNG: NVIDIA 480B (Sâu sắc nhất)
    try:
        url_nv = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers_nv = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
        res = requests.post(url_nv, headers=headers_nv, json={"model": NVIDIA_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}, timeout=360)
        res.raise_for_status()
        # Đảm bảo định dạng chuẩn OpenAI
        response_data = res.json()
        if "choices" in response_data and len(response_data["choices"]) > 0:
            content = response_data["choices"][0]["message"]["content"]
            return content, "Nvidia 480B"
        else:
            raise Exception("Invalid response format from NVIDIA API")
    except Exception:
        print("⚠️ Nvidia sập. Chuyển sang Groq...")

        # 2. LỚP PHẢN ỨNG NHANH: GROQ (Llama 3.1 70B)
        try:
            url_g = "https://api.groq.com/openai/v1/chat/completions"
            headers_g = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            # Sếp chú ý dùng model Llama 3.1 70B cho ổn định
            res = requests.post(url_g, headers=headers_g, json={"model": "llama-3.1-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}, timeout=360)
            res.raise_for_status()
            # Đảm bảo định dạng chuẩn OpenAI
            response_data = res.json()
            if "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0]["message"]["content"]
                return content, "Groq 70B"
            else:
                raise Exception("Invalid response format from Groq API")
        except Exception:
            print("⚠️ Groq sập. Kích hoạt lớp dự phòng Cloudflare...")

            # 3. LỚP DỰ PHÒNG CHIẾN LƯỢC: CLOUDFLARE WORKERS AI
            try:
                # Tận dụng Token Cloudflare sếp đã cấu hình
                cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
                cf_token = os.getenv("CLOUDFLARE_API_KEY")
                url_cf = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/qwen/qwen2.5-coder-32b-instruct"
                headers_cf = {"Authorization": f"Bearer {cf_token}"}
                res = requests.post(url_cf, headers=headers_cf, json={"messages": [{"role": "user", "content": prompt}]}, timeout=360)
                res.raise_for_status()
                # Đảm bảo định dạng chuẩn OpenAI
                response_data = res.json()
                if "result" in response_data and "response" in response_data["result"]:
                    content = response_data["result"]["response"]
                    return content, "Cloudflare AI (70B)"
                else:
                    raise Exception("Invalid response format from Cloudflare API")
            except Exception:
                print("⚠️ Cả 3 lớp Cloud đều chết! Chốt chặn cuối cùng: Local AI...")

                # 4. CHỐT CHẶN CUỐI CÙNG: LOCAL AI (OLLAMA)
                try:
                    url_l = "http://host.docker.internal:11434/v1/chat/completions"
                    res = requests.post(url_l, json={"model": "qwen2.5-coder:14b", "messages": [{"role": "user", "content": prompt}]}, timeout=360)
                    res.raise_for_status()
                    # Đảm bảo định dạng chuẩn OpenAI
                    response_data = res.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        content = response_data["choices"][0]["message"]["content"]
                        return content, "Local AI (Nội bộ)"
                    else:
                        raise Exception("Invalid response format from Local AI")
                except Exception:
                    raise Exception("Sập toàn tập 4 lớp! Vui lòng kiểm tra lại kết nối mạng hoặc Local AI.")

def generate_qa():
    send_telegram("🌌 <b>TRẠNG THÁI NGỦ SÂU:</b> AI đang tự tưởng tượng ra các kịch bản tấn công mạng để luyện tập...")
    
    # Tạo prompt để sinh QA
    prompt = """Hãy tạo một kịch bản tấn công mạng thực tế có thể xảy ra, bao gồm:
1. Mô tả lỗ hổng
2. Cách khai thác
3. Cách phòng thủ

Trả lời bằng tiếng Việt chuyên nghiệp, sử dụng các thẻ HTML <code> để đánh dấu phần kỹ thuật.
"""

    try:
        # Hỏi AI để tạo QA
        qa_content, used_model = ask_ai_with_failover(prompt)
        
        # Tạo ID cho document
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_id = f"dream_qa_{timestamp}"
        
        # Nhờ Cloudflare dịch kịch bản mơ ngủ thành Vector
        vector_data = get_embedding(qa_content)
        
        if vector_data:
            from pinecone import Pinecone
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            memory_index = pc.Index("evonet-memory")
            
            # Đẩy lên mây Pinecone
            memory_index.upsert(
                vectors=[{
                    "id": doc_id,
                    "values": vector_data,
                    "metadata": {
                        "source": "self_generated_dream",
                        "type": "qa_simulation",
                        "model": used_model,
                        "text": qa_content  # BẮT BUỘC có dòng này để lưu lại chữ cho sếp đọc
                    }
                }],
                namespace="learned_skills"  # Bỏ vào ngăn kéo Kỹ năng
            )
            preview = qa_content[:300].replace('<', '<').replace('>', '>')
            msg = f"💡 <b>TỰ SÁNG TẠO THÀNH CÔNG!</b>\n⚙️ <i>Tác giả: {used_model}</i>\n\nEm vừa nghĩ ra một kịch bản mới và đã lưu vào não bộ.\n\n<b>Trích lục:</b>\n<i>{preview}...</i>"
            send_telegram(msg)
            print("Tự đẻ bài thành công!")
    except Exception as e:
        send_telegram(f"❌ <b>Lỗi khi tự mơ:</b> {e}")

if __name__ == "__main__":
    generate_qa()
