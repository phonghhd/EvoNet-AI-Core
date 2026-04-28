import os
import requests
import datetime
from dotenv import load_dotenv
from multi_language_support import MultiLanguageSupport

# --- BƠM TIÊM CHÌA KHÓA SIÊU SẠCH ---
def get_env_safe(key_name):
    load_dotenv("/home/phong/evonet-core/.env", override=True)
    val = os.getenv(key_name)
    if val:
        # Tẩy rửa mọi ký tự tàng hình, nháy kép, dấu cách thừa
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None

# --- CẤU HÌNH LOCAL AI ---
LOCAL_AI_ENABLED = os.getenv("LOCAL_AI_ENABLED", "false").lower() == "true"
LOCAL_AI_MODEL = os.getenv("LOCAL_AI_MODEL", "qwen2.5-coder:14b")
LOCAL_AI_BASE_URL = os.getenv("LOCAL_AI_BASE_URL", "http://host.docker.internal:11434/v1")

# Cấu hình Models mới nhất
NVIDIA_MODEL = "qwen/qwen3-coder-480b-a35b-instruct"
GROQ_MODEL = "llama-3.3-70b-versatile"
CF_MODEL = "@cf/qwen/qwen2.5-coder-32b-instruct"

def send_telegram(msg):
    token = get_env_safe("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_safe("TELEGRAM_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try: requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except: pass

def get_embedding(text: str):
    cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env_safe("CLOUDFLARE_API_KEY")
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data.get("success"):
            return data["result"]["data"][0]
        return None
    except Exception as e:
        print(f"Lỗi dịch Vector: {e}")
        return None

def ask_ai_with_failover(prompt):
    """Pháo Đài 4 Lớp: Tích hợp Máy nghe lén WAF với Local AI ưu tiên"""
    nv_key = get_env_safe("NVIDIA_API_KEY")
    groq_key = get_env_safe("GROQ_API_KEY")
    cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env_safe("CLOUDFLARE_API_KEY")
    
    # Định nghĩa các lớp AI
    layers = [
        {
            "name": "NVIDIA",
            "url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"},
            "payload": {"model": NVIDIA_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
            "timeout": 360,
            "response_parser": lambda r: r.json()["choices"][0]["message"]["content"]
        },
        {
            "name": "GROQ",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            "payload": {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
            "timeout": 360,
            "response_parser": lambda r: r.json()["choices"][0]["message"]["content"]
        },
        {
            "name": "LOCAL",
            "url": f"{LOCAL_AI_BASE_URL}/chat/completions" if LOCAL_AI_ENABLED else None,
            "headers": {"Content-Type": "application/json"},
            "payload": {"model": LOCAL_AI_MODEL, "messages": [{"role": "user", "content": prompt}]},
            "timeout": 360,
            "response_parser": lambda r: r.json()["choices"][0]["message"]["content"]
        },
        {
            "name": "CLOUDFLARE",
            "url": f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/{CF_MODEL}",
            "headers": {"Authorization": f"Bearer {cf_key}"},
            "payload": {"messages": [{"role": "user", "content": prompt}]},
            "timeout": 360,
            "response_parser": lambda r: r.json()["result"]["response"]
        }
    ]
    
    # Xáo trộn các lớp để tránh quá tải bất kỳ dịch vụ nào
    # Trong môi trường production, có thể sắp xếp dựa trên metrics về latency/success rate
    import random
    random.shuffle(layers)
    
    # Thử từng lớp cho tới khi thành công
    for layer in layers:
        # Bỏ qua Local AI nếu không được bật
        if layer["name"] == "LOCAL" and not LOCAL_AI_ENABLED:
            continue
            
        # Bỏ qua lớp nếu URL không được cấu hình
        if not layer["url"]:
            continue
            
        try:
            print(f"🚀 Đang kết nối tới: {layer['name']}...")
            res = requests.post(layer["url"], headers=layer["headers"], json=layer["payload"], timeout=layer["timeout"])
            
            # Ghi log nếu không thành công
            if res.status_code != 200:
                print(f"❌ NỘI SOI {layer['name']} CHỬI: {res.text}")
                continue
                
            res.raise_for_status()
            # Đảm bảo định dạng chuẩn OpenAI
            response_data = res.json()
            if "choices" in response_data and len(response_data["choices"]) > 0:
                result = response_data["choices"][0]["message"]["content"]
                model_name = layer["name"]
                print(f"✅ {layer['name']} ĐÃ TRẢ LỜI!")
                return result, model_name
            elif "result" in response_data and "response" in response_data["result"]:
                result = response_data["result"]["response"]
                model_name = layer["name"]
                print(f"✅ {layer['name']} ĐÃ TRẢ LỜI!")
                return result, model_name
            else:
                print(f"❌ {layer['name']} TRẢ LỜI SAI ĐỊNH DẠNG")
                continue
        except Exception as e:
            print(f"⚠️ {layer['name']} SẬP NGUỒN ({e}). Thử lớp tiếp theo...")
            continue
    
    # Nếu tất cả đều thất bại
    raise Exception("Sập toàn tập 4 lớp AI!")

# --- VÒNG LẶP TIẾN HÓA CỐT LÕI ---
def evolve():
    send_telegram("🧬 <b>BẮT ĐẦU TIẾN HÓA:</b> Đang nghiên cứu tài liệu bảo mật mới...")
    print("Khởi động vòng lặp tự học...")
    
    # Initialize multi-language support
    mls = MultiLanguageSupport()
    
    try:
        pc_key = get_env_safe("PINECONE_API_KEY")
        from pinecone.pinecone import Pinecone
        pc = Pinecone(api_key=pc_key)
        memory_index = pc.Index("evonet-memory")
        
        dummy_vector = [0.0] * 768 
        results = memory_index.query(
            vector=dummy_vector, 
            top_k=1, 
            namespace="security_knowledge_clean",
            include_metadata=True
        )
        
        if not results.get('matches'):
            print("Chưa có lỗ hổng nào trong não để học.")
            return
            
        cve_id = results['matches'][0]['id']
        cve_text = results['matches'][0]['metadata'].get('text', 'Không có nội dung')

        # Analyze code in workspace to determine target language
        workspace_path = "/workspace"
        target_language = "python"  # Default to Python
        
        if os.path.exists(workspace_path):
            # Try to detect the predominant language in the workspace
            language_counts = {}
            for root, dirs, files in os.walk(workspace_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for file in files:
                    if file.endswith(tuple(sum(MultiLanguageSupport.SUPPORTED_LANGUAGES.values(), []))):
                        lang = MultiLanguageSupport().detect_language(file)
                        if lang:
                            language_counts[lang] = language_counts.get(lang, 0) + 1
            
            # Use the most common language, or default to Python
            if language_counts:
                target_language = max(language_counts, key=language_counts.get)
        
        # Create language-specific prompt
        language_names = {
            "python": "Python",
            "javascript": "Node.js/Javascript",
            "typescript": "TypeScript",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "csharp": "C#",
            "go": "Go",
            "rust": "Rust",
            "php": "PHP",
            "ruby": "Ruby",
            "swift": "Swift",
            "kotlin": "Kotlin"
        }
        
        language_name = language_names.get(target_language, "Python/Node.js")
        
        prompt = f"""
        Dưới đây là thông tin về một lỗ hổng bảo mật:
        {cve_text}

        Hãy:
        1. Giải thích ngắn gọn cơ chế lỗi.
        2. Viết code mẫu ({language_name}) để NGĂN CHẶN.
        BẮT BUỘC TRẢ LỜI BẰNG TIẾNG VIỆT CHUYÊN NGHIỆP.
        """

        defense_code, used_model = ask_ai_with_failover(prompt)

        vector_data = get_embedding(defense_code)
        if vector_data:
            from pinecone.pinecone import Pinecone
            pc_key = get_env_safe("PINECONE_API_KEY")
            pc = Pinecone(api_key=pc_key)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_id = f"skill_{cve_id}_{timestamp}"
            memory_index.upsert(
                vectors=[{
                    "id": doc_id,
                    "values": vector_data,
                    "metadata": {
                        "source": cve_id,
                        "type": "defense_skill",
                        "model_used": used_model,
                        "text": defense_code,
                        "language": target_language
                    }
                }],
                namespace="learned_skills"
            )

            # Also add to Knowledge Graph
            try:
                from kg_manager import get_kg_instance
                kg = get_kg_instance()
                if kg.driver is not None:
                    # Add defense skill node
                    skill_added = kg.add_defense_skill(
                        skill_id=doc_id,
                        description=defense_code,
                        model_used=used_model,
                        source_cve=cve_id,
                        confidence_score=0.8  # Default confidence, could be improved
                    )
                    if skill_added:
                        # Link defense skill to the CVE it mitigates
                        kg.link_defense_to_cve(skill_id=doc_id, cve_id=cve_id, relationship_type="MITIGATES")
                        print(f"📊 Đã thêm kĩ năng phòng thủ {doc_id} vào Knowledge Graph và liên kết với CVE {cve_id}")
                    else:
                        print(f"⚠️ Không thể thêm kĩ năng phòng thủ vào Knowledge Graph")
                else:
                    print(f"⚠️ Knowledge Graph không khả dụng, bỏ qua việc thêm kĩ năng phòng thủ")
            except Exception as e:
                print(f"⚠️ Lỗi khi tương tác với Knowledge Graph trong self_evolve: {e}")

            preview_text = defense_code[:400].replace('<', '<').replace('>', '>')
            msg = f"🧠 <b>TIẾN HÓA THÀNH CÔNG!</b>\n⚙️ <i>Phụ trách bởi: {used_model}</i>\n\nEm đã học xong cách chống lại <code>{cve_id}</code>.\n\n<b>Trích lục:</b>\n<i>{preview_text}...</i>"
            send_telegram(msg)
            print(f"✅ Tiến hóa thành công bằng {used_model}!")

    except Exception as e:
        error_msg = f"🚨 <b>LỖI HỆ THỐNG NGHIÊM TRỌNG:</b>\nTiến hóa thất bại. {e}"
        print(error_msg)
        send_telegram(error_msg)

if __name__ == "__main__":
    evolve()
