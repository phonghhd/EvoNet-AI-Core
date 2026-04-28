from datasets import load_dataset
import chromadb

def super_harvest():
    # Danh sách 6 "mỏ vàng" sếp muốn hút
    # Sếp có thể thêm bớt tùy ý
    m_vang = [
        {"name": "iamtarun/python_code_instructions_18k_alpaca", "q_col": "instruction", "a_col": "output"},
        {"name": "m-a-p/CodeFeedback-Filtered-Instruction", "q_col": "query", "a_col": "answer"},
        {"name": "bkai-foundation-models/vi-alpaca", "q_col": "instruction", "a_col": "output"},
	{"name": "vinai/PhoMath", "q_col": "instruction", "a_col": "output"},
	{"name": "spydaz/CyberSecurity", "q_col": "instruction", "a_col": "output"},
	{"name": "trelis/cybersecurity_vulnerabilities", "q_col": "instruction", "a_col": "output"},
    ]

    try:
        print("🔌 Đang kết nối Não bộ ChromaDB...")
        chroma_client = chromadb.HttpClient(host='evonet_vector_db', port=8000)
        skills_col = chroma_client.get_or_create_collection(name="learned_skills")

        for m in m_vang:
            repo = m["name"]
            print(f"\n🚀 Đang tiếp cận mỏ dữ liệu: {repo}...")
            
            try:
                # Chỉ lấy 500 dòng đầu tiên để bảo vệ phần cứng Mini PC
                dataset = load_dataset(repo, split="train[:500]")
                
                documents = []
                ids = []
                
                for i, row in enumerate(dataset):
                    # Bắt lỗi nếu cột dữ liệu trống
                    if not row.get(m["q_col"]) or not row.get(m["a_col"]): continue
                    
                    knowledge = f"Vấn đề: {row[m['q_col']]}\nGiải quyết: {row[m['a_col']]}"
                    documents.append(knowledge)
                    
                    # Tạo ID không đụng hàng
                    safe_repo_name = repo.replace("/", "_")
                    ids.append(f"hf_{safe_repo_name}_{i}")

                print(f"📦 Đang nạp {len(documents)} khối tri thức từ {repo} vào Não...")
                skills_col.add(documents=documents, ids=ids)
                print(f"✅ Hút xong mỏ {repo}!")
                
            except Exception as e_repo:
                print(f"⚠️ Bỏ qua mỏ {repo} vì lỗi cấu trúc/mạng: {e_repo}")

        print("\n🎉 HOÀN TẤT ĐẠI CHU TRÌNH BƠM DỮ LIỆU!")
        
    except Exception as e:
        print(f"❌ Lỗi hệ thống: {e}")

if __name__ == "__main__":
    super_harvest()
