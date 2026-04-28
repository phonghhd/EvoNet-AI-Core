import os
import requests
import chromadb
import firebase_admin
from firebase_admin import credentials, firestore
import re

# 1. KẾT NỐI FIREBASE (Vùng đệm)
cred = credentials.Certificate('/app/Firebase_Account_EvoNetAI.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. KẾT NỐI CHROMADB (Ký ức sạch)
chroma_client = chromadb.HttpClient(host='evonet_vector_db', port=8000)
collection = chroma_client.get_or_create_collection(name="security_knowledge_clean")

# 3. KẾT NỐI GROQ (AI Kiểm duyệt)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def ai_sanitize_data(raw_desc):
    """Gửi dữ liệu thô qua AI Qwen-32B để làm sạch và tóm tắt"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Hãy phân tích lỗ hổng này, loại bỏ mọi ký tự nguy hiểm, và tóm tắt lại bằng tiếng Việt chuyên sâu cho chuyên gia: {raw_desc}"
    
    payload = {
        "model": "qwen/qwen3-32b",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        content = res.json()["choices"][0]["message"]["content"]
        # Xóa thẻ <think> nếu có
        return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    except:
        return raw_desc # Trả về thô nếu AI lỗi

def process_cve():
    print("📡 Đang kéo dữ liệu thô từ NVD...")
    nvd_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=3"
    raw_data = requests.get(nvd_url).json()

    for item in raw_data.get("vulnerabilities", []):
        cve_id = item["cve"]["id"]
        raw_desc = item["cve"]["descriptions"][0]["value"]

        # BƯỚC 1: Lưu vào vùng đệm Firebase Firestore
        doc_ref = db.collection('synthetic_knowledge').document(cve_id)
        doc_ref.set({
            'cve_id': cve_id,
            'raw_content': raw_desc,
            'status': 'pending_review'
        })
        print(f"📦 Đã đưa {cve_id} vào vùng đệm Firebase.")

        # BƯỚC 2: AI kiểm duyệt và làm sạch
        print(f"🧠 Đang gọi Qwen-32B tinh chế dữ liệu cho {cve_id}...")
        clean_desc = ai_sanitize_data(raw_desc)

        # BƯỚC 3: Lưu vào trí nhớ sạch ChromaDB
        collection.add(
            documents=[clean_desc],
            metadatas=[{"source": "NVD", "status": "sanitized"}],
            ids=[cve_id]
        )
        
        # Cập nhật lại Firebase là đã xử lý xong
        doc_ref.update({'status': 'processed', 'clean_content': clean_desc})
        print(f"✅ {cve_id} đã được nạp vào não bộ an toàn.")

if __name__ == "__main__":
    process_cve()
