import os
import requests
from pinecone.pinecone import Pinecone
import firebase_admin
from firebase_admin import credentials, firestore
import re
from dotenv import load_dotenv
load_dotenv("/app/.env", override=True)

# 1. KẾT NỐI FIREBASE (Vùng đệm)
# cred = credentials.Certificate('/app/Firebase_Account_EvoNetAI.json')
# # Kiểm tra xem app đã được khởi tạo chưa để tránh lỗi chạy nhiều lần
# if not firebase_admin._apps:
#     firebase_admin.initialize_app(cred)
# db = firestore.client()

# --- 2. KẾT NỐI PINECONE CLOUD ---
# pinecone_key = os.getenv("PINECONE_API_KEY")
# pc = Pinecone(api_key=pinecone_key)
# memory_index = pc.Index("evonet-memory")

# --- HÀM DỊCH CHỮ THÀNH SỐ (BẰNG CLOUDFLARE) ---
def get_embedding(text: str):
    cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    cf_key = os.getenv("CLOUDFLARE_API_KEY")
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    
    try:
        res = requests.post(url, headers=headers, json={"text": [text]})
        data = res.json()
        if data.get("success"):
            return data["result"]["data"][0]
        return None
    except Exception as e:
        print(f"Lỗi dịch Vector: {e}")
        return None

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
        # Xóa thẻ ``` nếu có
        return re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
    except:
        return raw_desc # Trả về thô nếu AI lỗi

def extract_cwe_ids(description):
    """Extract CWE IDs from description"""
    import re
    # Simple pattern for CWE IDs
    cwe_pattern = r'CWE-\d{1,4}'
    matches = re.findall(cwe_pattern, description, re.IGNORECASE)
    return list(set(matches))  # Remove duplicates

def extract_affected_software(description):
    """Extract affected software from description (simplified)"""
    # This would ideally use NLP or a dictionary of known software
    # For now, we'll return an empty list and rely on other sources
    return []

def process_cve():
    print("📡 Đang kéo dữ liệu thô từ NVD...")
    nvd_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=3"
    new_cve_count = 0
    MAX_CVE_PER_RUN = 10
    raw_data = requests.get(nvd_url).json()

    for item in raw_data.get("vulnerabilities", []):
        if new_cve_count >= MAX_CVE_PER_RUN:
            print("🛑 Đã gom đủ 10 lỗ hổng mới. Dừng cào dữ liệu để xử lý!")
            break
            
        cve_id = item["cve"]["id"]
        raw_desc = item["cve"]["descriptions"][0]["value"]

        # ======================================================
        # TRẠM KIỂM LÂM FIREBASE: KIỂM TRA LỖ HỔNG ĐÃ HỌC CHƯA
        # ======================================================
        # doc_ref = db.collection('synthetic_knowledge').document(cve_id)
        
        # if doc_ref.get().exists:
        #     print(f"⏩ Lỗ hổng {cve_id} đã có trong hệ thống. Bỏ qua để tiết kiệm Token!")
        #     continue # Lệnh 'continue' ép vòng lặp bỏ qua các bước dưới, nhảy sang lỗ hổng tiếp theo
        # ======================================================

        # BƯỚC 1: Lưu vào vùng đệm Firebase Firestore
        # doc_ref.set({
        #     'cve_id': cve_id,
        #     'raw_content': raw_desc,
        #     'status': 'pending_review'
        # })
        print(f"📦 Đã đưa {cve_id} vào vùng đệm Firebase.")

        # BƯỚC 2: AI kiểm duyệt và làm sạch
        print(f"🧠 Đang gọi Qwen-32B tinh chế dữ liệu cho {cve_id}...")
        clean_desc = ai_sanitize_data(raw_desc)

        # BƯỚC 3: LƯU VÀO TRÍ NHỚ PINECONE CLOUD
        print(f"🔄 Đang nhờ Cloudflare dịch mã {cve_id} sang Toán học...")
        vector_data = get_embedding(clean_desc)
        
        # Extract additional data for KG
        cvss_score = None
        cwe_ids = []
        affected_software = []  # We'll leave empty for now due to complexity of configurations
        exploit_maturity = 'unknown'  # Placeholder, would need external data source
        published_date = ""

        try:
            cve_data = item["cve"]
            
            # Get published date
            published_date = cve_data.get("published", "")
            
            # Get CVSS score from metrics
            metrics = cve_data.get("metrics", {})
            if metrics:
                for key in ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
                    if key in metrics and metrics[key]:
                        metric = metrics[key][0]  # Take the first one
                        cvss_data = metric.get('cvssData', {})
                        cvss_score = cvss_data.get('baseScore')
                        break
            
            # Get CWE IDs from weaknesses
            weaknesses = cve_data.get("weaknesses", [])
            for weakness in weaknesses:
                for desc in weakness.get('description', []):
                    if desc.get('lang') == 'en':
                        value = desc.get('value')
                        if value and value.startswith('CWE-'):
                            cwe_ids.append(value)
            
            # If no CWE from weaknesses, try extracting from description
            if not cwe_ids:
                cwe_ids = extract_cwe_ids(raw_desc)
            
            # For affected software, we would need to parse configurations which is complex
            # For now, we'll leave it empty and note that this is a limitation
            # In a future improvement, we could parse the configurations node
            
        except Exception as e:
            print(f"⚠️ Lỗi khi trích xuất dữ liệu bổ sung cho CVE {cve_id}: {e}")
            # Continue with what we have

        # Store in Knowledge Graph if available
        try:
            from kg_manager import get_kg_instance
            kg = get_kg_instance()
            if kg.driver is not None:  # Check if KG is available
                # Add CVE node to KG
                cve_added = kg.add_cve_node(
                    cve_id=cve_id,
                    description=clean_desc,
                    cvss_score=cvss_score,
                    cwe_ids=cwe_ids,
                    affected_software=affected_software,
                    exploit_maturity=exploit_maturity,
                    published_date=published_date
                )
                
                if cve_added:
                    print(f"📊 Đã thêm CVE {cve_id} vào Knowledge Graph")
                else:
                    print(f"⚠️ Không thể thêm CVE {cve_id} vào Knowledge Graph")
            else:
                print(f"⚠️ Knowledge Graph không khả dụng, bỏ qua việc thêm CVE {cve_id}")
        except Exception as e:
            print(f"⚠️ Lỗi khi tương tác với Knowledge Graph: {e}")

        if vector_data:
            memory_index.upsert(
                vectors=[
                    {
                        "id": cve_id, 
                        "values": vector_data, 
                        "metadata": {
                            "source": "NVD", 
                            "status": "sanitized",
                            "text": clean_desc # Lưu lại chữ để sau này AI còn lấy ra đọc
                        }
                    }
                ],
                namespace="security_knowledge_clean" # Cho vào đúng ngăn kéo
            )
            print("☁️ Đã đẩy Vector lên mây Pinecone thành công!")
        else:
            print(f"⚠️ Lỗi dịch Vector, bỏ qua lưu Pinecone cho {cve_id}")        

        # Cập nhật lại Firebase là đã xử lý xong
        # Also store the enriched data in Firebase for future reference
        # doc_ref.update({
        #     'status': 'processed', 
        #     'clean_content': clean_desc,
        #     'cvss_score': cvss_score,
        #     'cwe_ids': cwe_ids,
        #     'affected_software': affected_software,
        #     'exploit_maturity': exploit_maturity,
        #     'published_date': published_date
        # })
        print(f"✅ {cve_id} đã được nạp vào não bộ an toàn.")
        new_cve_count += 1

if __name__ == "__main__":
    process_cve()
