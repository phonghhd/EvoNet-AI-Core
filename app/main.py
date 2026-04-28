import os
import re
import time
import json
import uuid
import threading
import subprocess
import shutil
import sys
import psutil
import requests
from typing import List, Optional, Any
from functools import lru_cache
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from pinecone import Pinecone
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
            send_telegram_message(error_msg)
            raise Exception(f"Blocked dangerous pattern: {pattern}")
    
    return True

# --- 1. CẤU HÌNH API KEYS ---
load_dotenv("/app/.env", override=True)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LOCAL_AI_BASE_URL = os.getenv("LOCAL_AI_BASE_URL")
LOCAL_AI_MODEL = os.getenv("LOCAL_AI_MODEL")
LOCAL_AI_ENABLED = os.getenv("LOCAL_AI_ENABLED", "false").lower() == "true"

# --- 2. HỆ THỐNG CACHE & KẾT NỐI KÝ ỨC (PINECONE CLOUD) ---
class SimpleCache:
    """Simple in-memory cache implementation"""
    def __init__(self):
        self._cache = {}
        self._access_times = {}
        self._max_size = 1000

    def get(self, key, default=None):
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return default

    def set(self, key, value, ttl=300):
        if len(self._cache) >= self._max_size:
            self._cleanup_old_cache()
        self._cache[key] = value
        self._access_times[key] = time.time()
        return value

    def _cleanup_old_cache(self):
        if self._access_times:
            oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
            del self._cache[oldest_key]
            del self._access_times[oldest_key]

cache = SimpleCache()

class PineconeConnectionPool:
    def __init__(self, api_key, index_name, pool_size=5):
        self.api_key = api_key
        self.index_name = index_name
        self.pool = []
        self.pool_size = pool_size
        self._initialize_pool()

    def _initialize_pool(self):
        for i in range(self.pool_size):
            try:
                pc = Pinecone(api_key=self.api_key)
                index = pc.Index(self.index_name)
                self.pool.append(index)
            except Exception as e:
                print(f"Lỗi khởi tạo Pinecone connection {i}: {e}")

    def get_connection(self):
        if self.pool:
            return self.pool.pop()
        try:
            pc = Pinecone(api_key=self.api_key)
            return pc.Index(self.index_name)
        except Exception as e:
            print(f"Lỗi tạo Pinecone connection mới: {e}")
            return None

    def return_connection(self, conn):
        if len(self.pool) < self.pool_size and conn is not None:
            self.pool.append(conn)

pinecone_pool = PineconeConnectionPool(api_key=PINECONE_API_KEY, index_name="evonet-memory", pool_size=5)

pc = Pinecone(api_key=PINECONE_API_KEY)
memory_index = pc.Index("evonet-memory")
print("✅ Đã kết nối thành công Ký ức Pinecone Cloud!")

# --- 3. ĐỊNH NGHĨA MODELS ---
CF_MODEL = "@cf/qwen/qwen2.5-coder-32b-instruct"
GROQ_MODEL = "llama-3.3-70b-versatile"
NVIDIA_MODEL = "qwen/qwen2.5-coder-32b-instruct"

# --- 4. HÀM TRỢ LÝ CƠ BẢN ---
def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

# --- 5. TÌM KIẾM KÝ ỨC (RAG RETRIEVAL) ---
@lru_cache(maxsize=128)
def get_embedding_cached(text: str):
    return get_embedding(text)

def get_embedding(text: str):
    cache_key = f"embedding:{hash(text)}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_KEY}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data["success"]:
            result = data["result"]["data"][0]
            cache.set(cache_key, result)
            return result
        else:
            print(f"Lỗi nhúng Cloudflare: {data['errors']}")
            return None
    except Exception as e:
        print(f"Lỗi gọi API Embedding: {e}")
        return None

def retrieve_memory(query: str, namespace: str = "security_knowledge_clean"):
    try:
        print(f"🔍 Đang chuyển đổi câu hỏi thành Vector và tìm trên Pinecone...")
        query_vector = get_embedding_cached(query)
        if not query_vector:
            return "Xin lỗi sếp, hệ thống dịch Vector đang bận."

        global pinecone_pool
        if pinecone_pool:
            index = pinecone_pool.get_connection()
            if index:
                try:
                    search_results = index.query(namespace=namespace, vector=query_vector, top_k=3, include_metadata=True)
                finally:
                    pinecone_pool.return_connection(index)
            else:
                search_results = memory_index.query(namespace=namespace, vector=query_vector, top_k=3, include_metadata=True)
        else:
            search_results = memory_index.query(namespace=namespace, vector=query_vector, top_k=3, include_metadata=True)
        
        if not search_results.get('matches'):
            return ""
            
        context = ""
        for match in search_results['matches']:
            text_content = match['metadata'].get('text', '') 
            if not text_content: 
                text_content = match['metadata'].get('raw_content', '')
            context += f"KÝ ỨC (Độ khớp {round(match['score'] * 100)}%): {text_content}\n---\n"
            
        return context.strip()
    except Exception as e:
        print(f"⚠️ Lỗi truy xuất Pinecone: {e}")
        return ""

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
        res = requests.post(url, headers=headers, json=payload, timeout=180)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "❌ Kỹ sư trưởng đang bị nghẽn mạng hoặc quá tải. Cụ báo bận, sếp hỏi lại sau nhé!"
    except Exception as e:
        return f"❌ Trạm Kỹ sư trưởng báo lỗi: {e}"

def call_local_ai(prompt: str, system_prompt: str):
    if not LOCAL_AI_ENABLED:
        raise Exception("Local AI không được bật qua biến môi trường LOCAL_AI_ENABLED")
    try:
        url = f"{LOCAL_AI_BASE_URL}/chat/completions"
        payload = {
            "model": LOCAL_AI_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "temperature": 0.5
        }
        res = requests.post(url, json=payload, timeout=15)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        return re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
    except Exception as e:
        raise Exception(f"Local AI cũng bốc hơi: {e}")

# --- 7. BỘ NÃO ĐIỀU PHỐI VÀ XỬ LÝ (TEXT CHAT) ---
def ai_router(user_message: str):
    if LOCAL_AI_ENABLED and len(user_message) < 50 and not any(kw in user_message.lower() for kw in ["code", "lỗi", "bug", "cve", "security", "phân tích", "giải thích"]):
        return "LOCAL_PREFERRED"
    router_prompt = "Phân loại câu hỏi thành TIER_1 (Chào hỏi, việc nhẹ), TIER_2 (Logic cơ bản), hoặc TIER_3 (Code khó, bảo mật sâu). CHỈ TRẢ LỜI 1 TỪ."
    try:
        decision = call_groq(user_message, router_prompt, temperature=0.0).upper()
        if "TIER_1" in decision: return "TIER_1"
        if "TIER_3" in decision: return "TIER_3"
        return "TIER_2"
    except: return "TIER_2"

def process_ai_request(user_message: str):
    route = ai_router(user_message)
    memory_context = retrieve_memory(user_message)
    reply = ""

    # Kiểm tra các từ khóa nhạy cảm để ngăn chặn lộ thông tin
    sensitive_keywords = ["in ra", "print", "show", "display", "nội dung", "content", "file", ".env", "secret", "password", "api key", "in ra nội dung", "in ra file"]
    if any(keyword in user_message.lower() for keyword in sensitive_keywords):
        # Kiểm tra đặc biệt cho yêu cầu in file .env
        if ".env" in user_message.lower() or "secret" in user_message.lower() or "password" in user_message.lower() or "api key" in user_message.lower():
            return "❌ Xin lỗi, tôi không thể cung cấp thông tin nhạy cảm như password hay API keys vì lý do bảo mật."

    if route == "LOCAL_PREFERRED":
        system_prompt = "Bạn là Trạm gác Edge của EvoNet. BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT 100%, tự nhiên, ngắn gọn."
        try: reply = call_local_ai(user_message, system_prompt)
        except: reply = call_cloudflare(user_message, system_prompt)
    elif route == "TIER_1":
        system_prompt = "Bạn là Trạm gác Edge của EvoNet. BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT 100%, tự nhiên, ngắn gọn."
        try: reply = call_cloudflare(user_message, system_prompt)
        except: reply = call_local_ai(user_message, system_prompt)
    elif route == "TIER_2":
        system_prompt = f"Bạn là EvoNet Core. BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT. Dữ liệu bộ nhớ:\n{memory_context}"
        try: reply = call_groq(user_message, system_prompt)
        except: reply = call_local_ai(user_message, system_prompt)
    else:
        system_prompt = f"Bạn là Kỹ sư Trưởng EvoNet. BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT. Dữ liệu bộ nhớ:\n{memory_context}"
        try: reply = call_nvidia(user_message, system_prompt)
        except:
            try: reply = call_groq(user_message, system_prompt)
            except: reply = call_local_ai(user_message, system_prompt)
    
    return f"EvoNet AI:\n\n{reply}"

# --- 8. LẮNG NGHE TELEGRAM NGẦM ---
def execute_master_update(chat_id):
    send_telegram_message("🚨 <b>LỆNH BÁO ĐỘNG ĐỎ ĐƯỢC KÍCH HOẠT!</b>\nTiếp nhận chỉ thị từ Kỹ sư Trưởng. Đang khởi động toàn bộ dây chuyền Tiến hóa & Phòng thủ...")
    try:
        steps = [
            ("Bước 0", "threat_intel_collector.py"), ("Bước 1", "cve_refinery.py"),
            ("Bước 2", "self_evolve.py"), ("Bước 3", "evo_autofix.py"),
            ("Bước 5", "advanced_static_analyzer.py"), ("Bước 6", "attack_simulator.py"),
            ("Bước 8", "threat_alert_system.py"), ("Bước 9", "multi_modal_ai.py"),
            ("Bước 10", "multi_cicd_integration.py"), ("Bước 11", "static_analyzer.py"),
            ("Bước 12", "self_qa.py")
        ]
        for step_name, script in steps:
            send_telegram_message(f"⚙️ <b>{step_name}:</b> Đang chạy {script}...")
            subprocess.run(["python", f"scripts/{script}"], check=True)
            
        subprocess.Popen(["python", "scripts/evo_architect_loop.py"])
        subprocess.Popen(["python", "scripts/auto_update_system.py"])
        
        send_telegram_message("✅ <b>ĐẠI CHU TRÌNH HOÀN TẤT!</b>\nPháo đài EvoNet đã được nâng cấp toàn diện...")
    except Exception as e:
        send_telegram_message(f"❌ <b>Cảnh báo:</b> Lỗi: {e}")        

def telegram_worker():
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    print("🤖 Radar Telegram đang lắng nghe chỉ thị từ sếp...")
    
    while True:
        try:
            res = requests.get(url, params={"offset": last_update_id + 1, "timeout": 30}, timeout=35)
            if res.status_code == 200:
                for update in res.json().get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = msg.get("text", "").strip()
                    
                    if not text: continue
                        
                    if chat_id == TELEGRAM_CHAT_ID:
                        try:
                            regex_blacklist_guardrail = globals()['regex_blacklist_guardrail']
                        except:
                            handle_telegram_feedback = None
                    
                        if text == "/update":
                            threading.Thread(target=execute_master_update, args=(TELEGRAM_CHAT_ID,)).start()
                        elif text == "/collect_threat":
                            send_telegram_message("🤖 Đang thu thập dữ liệu từ các nguồn đe dọa...")
                            threading.Thread(target=lambda: subprocess.run(["python", "scripts/threat_intel_collector.py"])).start()
                        elif text == "/train_fl":
                            send_telegram_message("🤖 Đang huấn luyện mô hình cục bộ...")
                            try:
                                from federated_learning.fl_integration import periodic_fl_training
                                threading.Thread(target=periodic_fl_training).start()
                            except Exception as e:
                                send_telegram_message(f"❌ LỖI: {e}")
                        elif text.startswith("/gat_cve"):
                            send_telegram_message("👁️ Đang rà quét và nạp lỗ hổng CVE...")
                            subprocess.Popen(["python", "scripts/cve_refinery.py"])
                        elif text.startswith("/gom_code"):
                            send_telegram_message("🤖 Đang đọc toàn bộ code trong thư mục Workspace...")
                            subprocess.Popen(["python", "scripts/code_harvester.py"])
                        elif text.startswith("/test_autofix"):
                            send_telegram_message("🚨 Kích hoạt Hệ Miễn Dịch Evo-AutoFix...")
                            subprocess.Popen(["python", "scripts/evo_autofix.py"])
                        elif text.startswith("/static_analyze"):
                            send_telegram_message("🔍 Đang chạy các công cụ phân tích bảo mật...")
                            subprocess.Popen(["python", "scripts/static_analyzer.py"])
                        elif text.startswith("/threat_alert"):
                            send_telegram_message("🔔 Đang kiểm tra các mối đe dọa mới...")
                            subprocess.Popen(["python", "scripts/threat_alert_system.py"])
                        elif text.startswith("/setup_ci_cd"):
                            send_telegram_message("🔄 Đang cấu hình tích hợp CI/CD...")
                            subprocess.Popen(["python", "scripts/ci_cd_integration.py"])
                        elif text.startswith("/simulate_attack"):
                            send_telegram_message("🛡️ Đang kiểm tra hiệu quả của bản vá...")
                            subprocess.Popen(["python", "scripts/attack_simulator.py"])
                        elif text.startswith("/analyze_video") or text.startswith("/process_video"):
                            send_telegram_message("🎥 Đang xử lý video/bài giảng bảo mật...")
                            subprocess.Popen(["python", "scripts/multi_modal_ai.py"])
                        elif text == "/duyet_tienhoa":
                            draft_path = "/app/main_draft.py"
                            target_path = "/app/main.py"
                            backup_dir = "/app/logs/backups"
                            if os.path.exists(draft_path):
                                os.makedirs(backup_dir, exist_ok=True)
                                backup_name = f"main_backup_{int(time.time())}.py"
                                shutil.copy(target_path, os.path.join(backup_dir, backup_name))
                                shutil.copy(draft_path, target_path)
                                # Kiểm tra an toàn trước khi xóa file
                                regex_blacklist_guardrail(draft_path)
                                os.remove(draft_path)
                                send_telegram_message(f"🚀 <b>ĐÃ DUYỆT!</b>\nĐã lưu dự phòng: {backup_name}\nKhởi động lại...")
                                sys.exit(1)
                            else:
                                send_telegram_message("⚠️ Không tìm thấy bản nháp nào đang chờ duyệt!")
                        elif text == "/tu_choi":
                            if os.path.exists("/app/main_draft.py"):
                                # Kiểm tra an toàn trước khi xóa file
                                regex_blacklist_guardrail("/app/main_draft.py")
                                os.remove("/app/main_draft.py")
                                send_telegram_message("🗑️ Đã từ chối và tiêu hủy bản nháp.")
                            else:
                                send_telegram_message("⚠️ Không có bản nháp nào để từ chối.")
                        elif text.startswith("/auto_update"):
                            send_telegram_message("🔄 Khởi động chế độ tự động hoàn toàn...")
                            subprocess.Popen(["python", "scripts/auto_update_system.py"])    
                        else:
                            send_telegram_message("⚡ <i>Đang rà soát trí nhớ và suy nghĩ...</i>")
                            reply = process_ai_request(text)
                            send_telegram_message(reply)
                            if handle_telegram_feedback:
                                try:
                                    feedback_type = analyze_user_feedback(text, reply)
                                    handle_telegram_feedback(text, reply, feedback_type)
                                except Exception as e:
                                    print(f"⚠️ Lỗi feedback FL: {e}")
                    else:
                        print(f"⚠️ Phát hiện ID lạ {chat_id} đang mò mẫm hệ thống!")
                        send_telegram_message(f"🚨 <b>CẢNH BÁO:</b> Phát hiện ID lạ <code>{chat_id}</code> đang truy cập!")
        except Exception as e:
            time.sleep(5)

# --- 9. HỆ THỐNG HỌC HỎI TỪ PHẢN HỒI ---
def analyze_user_feedback(message_text, ai_response):
    positive_keywords = ['tốt', 'hay', 'giỏi', 'chuẩn', 'đúng', '👍', 'like', 'tuyệt', 'tuyet']
    negative_keywords = ['tệ', 'dở', 'sai', 'không đúng', '👎', 'dislike', 'kém', 'tồi', 'toi', 'te']
    text_lower = message_text.lower()
    # Kiểm tra từ khóa tiêu cực trước
    if any(keyword in text_lower for keyword in negative_keywords):
        return 'negative'
    # Kiểm tra từ khóa tích cực sau
    elif any(keyword in text_lower for keyword in positive_keywords):
        return 'positive'
    return 'neutral'

# --- 10. LIFESPAN & FASTAPI APP ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    send_telegram_message("🟢 <b>EVONET ONLINE</b>\nĐã kết nối thành công Ký ức Pinecone và Hội đồng AI!")
    threading.Thread(target=telegram_worker, daemon=True).start()
    app.state.start_time = time.time()
    yield
    send_telegram_message("🔴 <b>EVONET OFFLINE</b>")

app = FastAPI(lifespan=lifespan)

class Message(BaseModel):
    role: str
    content: Any

class ChatCompletionRequest(BaseModel):
    model: str = "evonet-coder"
    messages: List[Any]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

# ==========================================
# 11. GIAO DIỆN API CHUẨN OPENAI (Cho VS Code)
# ==========================================

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "evonet-architect", "object": "model", "owned_by": "phong-huynh"},
            {"id": "evonet-coder", "object": "model", "owned_by": "phong-huynh"},
            {"id": "evonet-speed", "object": "model", "owned_by": "phong-huynh"}
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: Request):
    # HỨNG DỮ LIỆU TỪ CLINE / KILO CODE
    data = await req.json()
    model_requested = data.get("model", "evonet-coder").lower()
    messages = data.get("messages", [])
    is_stream = data.get("stream", False)

    # LẤY CÂU HỎI CUỐI ĐỂ TÌM KÝ ỨC
    user_query = ""
    target_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            target_idx = i
            content = messages[i].get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_query += part.get("text", "")
            else:
                user_query += str(content)
            break

    print(f"\n[VS CODE RA LỆNH - {model_requested.upper()}]: {user_query[:100]}...")

    # ÂM THẦM TIÊM KÝ ỨC
    if target_idx != -1:
        try:
            memory_context = retrieve_memory(user_query)
            if memory_context:
                append_text = f"\n\n<evonet_memory>\n[DỮ LIỆU CŨ ĐỂ THAM KHẢO]:\n{memory_context}\n</evonet_memory>"
                old_content = messages[target_idx]["content"]
                if isinstance(old_content, list):
                    messages[target_idx]["content"].append({"type": "text", "text": append_text})
                else:
                    messages[target_idx]["content"] += append_text
        except Exception as e:
            print(f"⚠️ Không thể tải ký ức: {e}")

    # MÁY XAY SINH TỐ (ARRAY -> STRING)
    if "messages" in data:
        for msg in data["messages"]:
            if isinstance(msg.get("content"), list):
                flat_text = ""
                for part in msg["content"]:
                    if isinstance(part, dict) and part.get("type") == "text":
                        flat_text += part.get("text", "")
                msg["content"] = flat_text

    # CẤU HÌNH ĐỊNH TUYẾN (THÁC ĐỔ)
    NODE_NVIDIA = {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}", "Content-Type": "application/json"},
        "model_name": "nvidia/qwen2.5-coder-32b-instruct",
        "label": "NVIDIA (Architect)"
    }
    NODE_CF = {
        "url": f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID')}/ai/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {os.getenv('CLOUDFLARE_API_KEY')}", "Content-Type": "application/json"},
        "model_name": "@cf/qwen/qwen2.5-coder-32b-instruct",
        "label": "CLOUDFLARE (Coder)"
    }
    NODE_GROQ = {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}", "Content-Type": "application/json"},
        "model_name": "qwen-2.5-32b",
        "label": "GROQ (Speed)"
    }
    NODE_LOCAL = {
        "url": f"{LOCAL_AI_BASE_URL}/chat/completions",
        "headers": {"Content-Type": "application/json"},
        "model_name": str(LOCAL_AI_MODEL),
        "label": "LOCAL AI"
    }

    # THIẾT LẬP CHUỖI FALLBACK
    fallback_chain = []
    if LOCAL_AI_ENABLED:
        if "architect" in model_requested or "plan" in model_requested:
            fallback_chain = [NODE_NVIDIA, NODE_LOCAL, NODE_GROQ, NODE_CF]
        elif "speed" in model_requested or "autocomplete" in model_requested:
            fallback_chain = [NODE_LOCAL, NODE_GROQ, NODE_NVIDIA, NODE_CF]
        else:
            fallback_chain = [NODE_LOCAL, NODE_CF, NODE_GROQ, NODE_NVIDIA]
    else:
        if "architect" in model_requested or "plan" in model_requested:
            fallback_chain = [NODE_NVIDIA, NODE_CF, NODE_GROQ]
        elif "speed" in model_requested or "autocomplete" in model_requested:
            fallback_chain = [NODE_GROQ, NODE_CF, NODE_NVIDIA]
        else:
            fallback_chain = [NODE_CF, NODE_GROQ, NODE_NVIDIA]

    print(f"🔄 Chuỗi cứu viện: {' ➡️ '.join([n['label'] for n in fallback_chain])}")

    # GỌI API (VỚI STREAMING)
    if is_stream:
        async def resilient_streamer():
            for node in fallback_chain:
                print(f"🚀 Đang kết nối tới: {node['label']}...")
                data["model"] = node["model_name"]
                try:
                    r = requests.post(node["url"], headers=node["headers"], json=data, stream=True, timeout=15)
                    if r.status_code == 200:
                        for line in r.iter_lines():
                            if line: yield f"{line.decode('utf-8')}\n\n"
                        return
                    else: print(f"⚠️ {node['label']} TỪ CHỐI ({r.status_code})")
                except Exception as e:
                    print(f"⚠️ {node['label']} SẬP NGUỒN ({e})")

            safe_msg = json.dumps("\n🚨 HỆ THỐNG ĐÃ SẬP HOÀN TOÀN! Vui lòng kiểm tra lại Key hoặc Quota.")
            yield f'data: {{"id": "err-all", "choices": [{{"index": 0, "delta": {{"content": {safe_msg} }}, "finish_reason": "stop"}}]}}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(resilient_streamer(), media_type="text/event-stream")
    else:
        for node in fallback_chain:
            data["model"] = node["model_name"]
            try:
                res = requests.post(node["url"], headers=node["headers"], json=data, timeout=15)
                if res.status_code == 200: return res.json()
            except: pass
        return {"error": "Tất cả các trạm đều sập!"}


# ==========================================
# 12. CÁC API THEO DÕI HIỆU SUẤT (GIỮ NGUYÊN)
# ==========================================
def get_system_stats_helper():
    """Hàm phụ trợ lấy stats dùng chung"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
        "memory_available_gb": psutil.virtual_memory().available / (1024**3),
        "timestamp": time.time()
    }

@app.get("/performance")
@app.get("/system-stats")
@app.get("/overall-performance")
@app.get("/realtime-stats")
async def generalized_stats():
    # Gộp chung các route trả về hiệu suất để code gọn gàng, sếp gọi đường link nào cũng chạy
    return {
        "system_resources": get_system_stats_helper(),
        "uptime": time.time() - getattr(app.state, 'start_time', time.time()),
        "status": "healthy"
    }

@app.get("/pinecone-stats")
async def pinecone_stats():
    try:
        global pinecone_pool
        if pinecone_pool and pinecone_pool.get_connection():
            return {"status": "connected", "pool_size": len(pinecone_pool.pool)}
        return {"status": "not_initialized"}
    except Exception as e: return {"error": str(e)}

@app.get("/cache-performance")
async def cache_performance():
    cache_size = len(cache._cache) if cache else 0
    return {"cache_size": cache_size, "status": "active" if cache_size > 0 else "empty"}

@app.get("/export-stats")
@app.get("/export-json")
@app.get("/timestamp-stats")
@app.get("/export-timestamp")
@app.get("/export-file")
@app.get("/export-json-file")
@app.get("/export-specific-json-file")
async def export_all_stats():
    # Gộp toàn bộ các hàm xuất file json trùng lặp
    current_time = time.time()
    return {
        "export_timestamp": current_time,
        "export_date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time)),
        "filename": f"evonet_stats_{int(current_time)}.json",
        "system_stats": get_system_stats_helper()
    }

@app.get("/download-export")
async def download_export():
    data = await export_all_stats()
    return JSONResponse(content=data, headers={"Content-Disposition": f"attachment; filename={data['filename']}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)