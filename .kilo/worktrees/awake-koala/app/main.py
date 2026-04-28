import subprocess
import threading
import subprocess
import os
import requests
import re
import threading
import time
import chromadb # THÊM THƯ VIỆN NÀY
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

# --- 1. CẤU HÌNH API KEYS ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- 2. KẾT NỐI KÝ ỨC (CHROMADB) ---
try:
    chroma_client = chromadb.HttpClient(host='evonet_vector_db', port=8000)
    # Kết nối tới 2 kho dữ liệu sếp đã tạo
    cve_collection = chroma_client.get_or_create_collection(name="security_knowledge_clean")
    code_collection = chroma_client.get_or_create_collection(name="personal_codebase")
    skills_collection = chroma_client.get_or_create_collection(name="learned_skills") 
    print("✅ Đã kết nối thành công Ký ức ChromaDB")
except Exception as e:
    print(f"⚠️ Lỗi kết nối ChromaDB: {e}")

# --- 3. ĐỊNH NGHĨA MODELS ---
CF_MODEL = "@cf/meta/llama-3.1-70b-instruct"
GROQ_MODEL = "llama-3.1-70b-versatile"
NVIDIA_MODEL = "qwen/qwen3-coder-480b-a35b-instruct"

# --- 4. HÀM TRỢ LÝ TELEGRAM ---
def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass


# --- 5. TÌM KIẾM KÝ ỨC (RAG RETRIEVAL) ---
def retrieve_memory(query: str):
    context = ""
    try:
        # Lục kho Security
        cve_results = cve_collection.query(query_texts=[query], n_results=1)
        if cve_results['documents'] and cve_results['documents'][0]:
            context += f"\n[Kiến thức Bảo mật nội bộ]: {cve_results['documents'][0][0]}"
            
        # Lục kho Code của sếp
        code_results = code_collection.query(query_texts=[query], n_results=1)
        if code_results['documents'] and code_results['documents'][0]:
            context += f"\n[Di sản Code nội bộ]: {code_results['documents'][0][0]}"

        # LỤC KHO TUYỆT CHIÊU AI VỪA TỰ HỌC
        skill_results = skills_collection.query(query_texts=[query], n_results=1)
        if skill_results['documents'] and skill_results['documents'][0]:
            context += f"\n[Kỹ năng tự tạo (Tuyệt chiêu)]: {skill_results['documents'][0][0]}"
            
    except Exception as e:
        print(f"Lỗi truy xuất ký ức: {e}")
        
    return context
# --- 6. CÁC HÀM GIAO TIẾP VỚI AI LÕI ---
def call_cloudflare(prompt: str, system_prompt: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_MODEL}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_KEY}", "Content-Type": "application/json"}
    payload = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]}
    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    return res.json()["result"]["response"]

def call_groq(prompt: str, system_prompt: str, temperature=0.6):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": temperature
    }
    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    content = res.json()["choices"][0]["message"]["content"]
    return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

def call_nvidia(prompt: str, system_prompt: str):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": NVIDIA_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096
    }
    try:
        # THÊM TIMEOUT 60 GIÂY VÀO ĐÂY!
        res = requests.post(url, headers=headers, json=payload, timeout=180)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "❌ Kỹ sư trưởng đang bị nghẽn mạng hoặc quá tải. Cụ báo bận, sếp hỏi lại sau nhé!"
    except Exception as e:
        return f"❌ Trạm Kỹ sư trưởng báo lỗi: {e}"
# --- 7. BỘ NÃO ĐIỀU PHỐI VÀ XỬ LÝ ---
def ai_router(user_message: str):
    router_prompt = "Phân loại câu hỏi thành TIER_1 (Chào hỏi, việc nhẹ), TIER_2 (Logic cơ bản), hoặc TIER_3 (Code khó, bảo mật sâu). CHỈ TRẢ LỜI 1 TỪ."
    try:
        decision = call_groq(user_message, router_prompt, temperature=0.0).upper()
        if "TIER_1" in decision: return "TIER_1"
        if "TIER_3" in decision: return "TIER_3"
        return "TIER_2"
    except: return "TIER_2"

def call_local_ai(prompt: str, system_prompt: str):
    """Vũ khí tối thượng: AI chạy bằng điện nhà sếp"""
    try:
        url = "http://host.docker.internal:11434/v1/chat/completions"
        payload = {
            "model": "qwen2.5-coder:14b", # Sếp nhớ tải con này trên VPS sau nhé
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5
        }
        res = requests.post(url, json=payload, timeout=15)
        res.raise_for_status()
        import re
        content = res.json()["choices"][0]["message"]["content"]
        return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    except Exception as e:
        raise Exception(f"Local AI cũng bốc hơi: {e}")

# --- ĐẠI TU BỘ ĐỊNH TUYẾN (ROUTER) CÓ BACKUP ---
def process_ai_request(user_message: str):
    # 1. Router phân loại độ khó
    route = categorize_intent(user_message)
    memory_context = retrieve_memory(user_message)
    
    reply = ""
    processor = ""

    if route == "TIER_1":
        system_prompt = "Bạn là Trạm gác Edge của EvoNet. BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT 100%, tự nhiên, ngắn gọn."
        try:
            reply = call_cloudflare(user_message, system_prompt)
            processor = "Cloudflare Edge"
        except Exception:
            # CF Sập -> Gọi Local
            reply = call_local_ai(user_message, system_prompt)
            processor = "Local AI (Fallback từ CF)"

    elif route == "TIER_2":
        system_prompt = f"Bạn là EvoNet Core. BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT. Dữ liệu bộ nhớ:\n{memory_context}"
        try:
            reply = call_groq(user_message, system_prompt)
            processor = "Groq"
        except Exception:
            # Groq Sập -> Gọi Local
            reply = call_local_ai(user_message, system_prompt)
            processor = "Local AI (Fallback từ Groq)"

    else:
        system_prompt = f"Bạn là Kỹ sư Trưởng EvoNet. BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT. Dữ liệu bộ nhớ:\n{memory_context}"
        try:
            reply = call_nvidia(user_message, system_prompt)
            processor = "Nvidia NIM"
        except Exception:
            # Nvidia Sập -> Gọi Groq -> Nếu Groq sập -> Gọi Local
            try:
                reply = call_groq(user_message, system_prompt)
                processor = "Groq (Fallback từ Nvidia)"
            except:
                reply = call_local_ai(user_message, system_prompt)
                processor = "Local AI (Trùm cuối xuất hiện)"

    return f"EvoNet AI:\n\n{reply}"
# --- 8. LẮNG NGHE TELEGRAM NGẦM ---
# --- HÀM THỰC THI ĐẠI CHU TRÌNH (CHẠY NGẦM ĐỂ KHÔNG ĐƠ BOT) ---
def execute_master_update(chat_id):
    # Đã sửa thành send_telegram_message cho đồng bộ
    send_telegram_message("🚨 <b>LỆNH BÁO ĐỘNG ĐỎ ĐƯỢC KÍCH HOẠT!</b>\nTiếp nhận chỉ thị từ Kỹ sư Trưởng. Đang khởi động toàn bộ dây chuyền Tiến hóa & Phòng thủ...")

    try:
        # Bước 1: Mắt thần quét NVD
        send_telegram_message("👁️ <b>Tiến trình 1/3:</b> Mắt thần đang quét và kéo lỗ hổng bảo mật mới nhất trên toàn cầu...")
        subprocess.run(["python", "scripts/cve_refinery.py"], check=True)

        # Bước 2: Ép AI học ngay lập tức
        send_telegram_message("🧠 <b>Tiến trình 2/3:</b> Não bộ (Nvidia/Groq/Local) đang phân tích lỗ hổng và tự viết tuyệt chiêu phòng thủ...")
        subprocess.run(["python", "scripts/self_evolve.py"], check=True)

        # Bước 3: Rà quét lỗi hệ thống và tự vá code (Hệ miễn dịch)
        send_telegram_message("🛡️ <b>Tiến trình 3/3:</b> Hệ miễn dịch đang rà soát log lỗi nội bộ và tự động mở Pull Request vá code...")
        subprocess.run(["python", "scripts/evo_autofix.py"], check=True)

        send_telegram_message("✅ <b>ĐẠI CHU TRÌNH HOÀN TẤT!</b>\nPháo đài EvoNet đã được nâng cấp lên trạng thái bảo mật cao nhất.")
        
    except Exception as e:
        # ĐÃ CĂN LỀ CHUẨN THẲNG HÀNG VỚI CHỮ "try" Ở TRÊN
        send_telegram_message(f"❌ <b>Cảnh báo:</b> Quá trình báo động đỏ bị gián đoạn. Lỗi: {e}")




def telegram_worker():
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    print("🤖 Radar Telegram đang lắng nghe chỉ thị từ sếp...")
    
    while True:
        try:
            # Lắng nghe tin nhắn mới (chờ tối đa 30s để không tốn CPU)
            res = requests.get(url, params={"offset": last_update_id + 1, "timeout": 30}, timeout=35)
            
            if res.status_code == 200:
                for update in res.json().get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = msg.get("text", "").strip()
                    
                    if not text:
                        continue
                        
                    # ==========================================
                    # BỨC TƯỜNG LỬA: KIỂM TRA QUYỀN LỰC SẾP PHONG
                    # ==========================================
                    if chat_id == TELEGRAM_CHAT_ID:
                        
                        # --- 1. NÚT BẤM HẠT NHÂN TỐI THƯỢNG ---
                        if text == "/update":
                            threading.Thread(target=execute_master_update, args=(TELEGRAM_CHAT_ID,)).start()
                        
                        # --- 2. CÁC LỆNH ĐIỀU KHIỂN TAY ---
                        elif text.startswith("/gat_cve"):
                            send_telegram_message("👁️ <b>MẮT THẦN KÍCH HOẠT:</b> Đang rà quét và nạp lỗ hổng CVE từ NVD vào ChromaDB...")
                            subprocess.Popen(["python", "scripts/cve_refinery.py"])
                            
                        elif text.startswith("/gom_code"):
                            send_telegram_message("🤖 <b>CÁNH TAY ROBOT:</b> Đang đọc toàn bộ code trong thư mục Workspace...")
                            subprocess.Popen(["python", "scripts/code_harvester.py"])
                            
                        elif text.startswith("/test_autofix"):
                            send_telegram_message("🚨 <b>GIẢ LẬP SẬP HỆ THỐNG:</b> Kích hoạt Hệ Miễn Dịch Evo-AutoFix...")
                            subprocess.Popen(["python", "scripts/evo_autofix.py"])
                            
                        # --- 3. NẾU LÀ TIN NHẮN CHAT BÌNH THƯỜNG ---
                        else:
                            send_telegram_message("⚡ <i>Đang rà soát trí nhớ và suy nghĩ...</i>")
                            # Chuyển tin nhắn cho Hệ thống Router AI xử lý (Có Failover 3 lớp)
                            reply = process_ai_request(text)
                            send_telegram_message(reply)
                            
                    # ==========================================
                    # NẾU KẺ LẠ MẶT (KHÁC CHAT_ID CỦA SẾP) NHẮN TIN
                    # ==========================================
                    else:
                        print(f"⚠️ Phát hiện ID lạ {chat_id} đang mò mẫm hệ thống!")
                        # Báo cáo về cho sếp biết có kẻ đang gõ cửa
                        send_telegram_message(f"🚨 <b>CẢNH BÁO BẢO MẬT:</b> Phát hiện ID lạ <code>{chat_id}</code> đang cố gắng giao tiếp với EvoNet!")
                        
        except Exception as e:
            # Nếu đứt mạng, ngủ 5s rồi thử kết nối lại, tránh spam lỗi làm sập NUC
            print(f"Lỗi Radar Telegram: {e}")
            time.sleep(5)


# --- 9. LIFESPAN & API ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    send_telegram_message("🟢 <b>EVONET ONLINE</b>\nĐã nạp xong Trí nhớ ChromaDB và Hội đồng AI!")
    threading.Thread(target=telegram_worker, daemon=True).start()
    yield
    send_telegram_message("🔴 <b>EVONET OFFLINE</b>")

app = FastAPI(lifespan=lifespan)
class ChatRequest(BaseModel): message: str

@app.post("/ask")
def ask_api(req: ChatRequest):
    return {"evonet_reply": process_ai_request(req.message)}

