import os
import chromadb

# Kết nối ChromaDB
chroma_client = chromadb.HttpClient(host='evonet_vector_db', port=8000)
# Tạo một vùng não riêng biệt chỉ để chứa Code
collection = chroma_client.get_or_create_collection(name="personal_codebase")

WORKSPACE_DIR = "/workspace"
# Bộ lọc thông minh: Tránh việc AI đọc nhầm file rác làm nổ RAM
IGNORE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".next", "build", "dist"}
ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md"}

def chunk_text(text, max_chars=2000):
    """Băm code ra thành từng cục nhỏ 2000 ký tự để AI dễ tiêu hóa"""
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def ingest_code():
    print("🤖 Đang kích hoạt Cánh tay Robot gom Code...")
    count = 0
    
    for root, dirs, files in os.walk(WORKSPACE_DIR):
        # Chặn ngay từ vòng gửi xe các thư mục rác
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Băm nhỏ và nhét vào não
                    chunks = chunk_text(content)
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{file_path}_chunk_{i}"
                        collection.add(
                            documents=[chunk],
                            metadatas=[{"source": file_path, "type": "code", "language": ext}],
                            ids=[doc_id]
                        )
                    print(f"✅ Đã nạp thành công: {file}")
                    count += 1
                except Exception as e:
                    print(f"⚠️ Bỏ qua file {file}: {e}")
                    
    print(f"🎉 Hoàn tất! Đã nạp {count} file code vào vùng não EvoNet.")

if __name__ == "__main__":
    ingest_code()
