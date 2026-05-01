import json
import os
import sys

# Thêm thư mục gốc vào path để import các module mới
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Chuyển toàn bộ Import lên đầu file để tối ưu hiệu năng (Chuẩn PEP8)
try:
    from brain.real_brain import qwen_brain
    from brain.storage import vector_storage
    from brain.remote_control import send_patch_approval_request
    HAS_BRAIN_MODULES = True
except ImportError as e:
    print(f"⚠️ Cảnh báo: Chưa tìm thấy các module não bộ ({e}). EvoNet sẽ chạy ở chế độ giả lập (Dummy Mode).")
    HAS_BRAIN_MODULES = False

# 1. Khai báo 2 địa chỉ rõ ràng (Bếp một chiều)
INPUT_FILE = "data/latest_threats.json"       # File kéo từ GitHub về (Chỉ đọc)
OUTPUT_FILE = "data/ai_generated_patches.json"  # File của AI tự tạo (Chỉ ghi)

def run_local_ai_patcher():
    # Kiểm tra xem GitHub đã giao hàng chưa
    if not os.path.exists(INPUT_FILE):
        print("💤 Chưa có nguyên liệu CVE mới từ GitHub.")
        return

    # 2. ĐỌC NGUYÊN LIỆU THÔ
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        cves = json.load(f)

    # Nạp dữ liệu cũ của AI (nếu có) để không bị ghi đè mất code cũ
    ai_patches = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            ai_patches = json.load(f)

    processed_count = 0

    # 3. KÍCH HOẠT NÃO BỘ EVONET
    for cve_id, details in cves.items():
        # Chỉ xử lý những file đã được Bot 3 dán nhãn sẵn sàng và chưa từng vá
        if details.get("stage") == "3_Ready_for_Fine_Tuning" and cve_id not in ai_patches:
            print(f"\n🧠 EvoNet đang phân tích lỗ hổng {cve_id}...")
            
            generated_patch_code = ""
            mitigation = "Cập nhật thư viện lên bản mới nhất và lọc input đầu vào."

            # Nếu sếp đã code xong 3 file kia thì chạy thật, chưa thì chạy giả lập
            if HAS_BRAIN_MODULES:
                try:
                    # 3.1 Nhờ Qwen sinh code
                    generated_patch_code = qwen_brain.generate_patch_code(cve_id, details)
                    
                    # 3.2 Lưu vào Pinecone
                    vector_id = vector_storage.store_patch_knowledge(cve_id, details)
                    if vector_id:
                        print(f"💾 Đã lưu bản vá cho {cve_id} vào Vector DB (ID: {vector_id})")
                        
                    # 3.3 Gửi báo cáo Telegram
                    patch_summary = generated_patch_code[:500] + "..." if len(generated_patch_code) > 500 else generated_patch_code
                    send_patch_approval_request(cve_id, patch_summary)
                    print(f"📲 Đã gửi yêu cầu duyệt qua Telegram cho sếp!")
                    
                except Exception as e:
                    print(f"❌ Lỗi hệ thống thần kinh trung ương: {e}")
                    generated_patch_code = "Lỗi trong quá trình AI sinh code."
            else:
                # Chỗ này đã được sửa lỗi chuỗi nhiều dòng bằng 3 dấu ngoặc kép
                generated_patch_code = """def fix_vulnerability():
    return 'patched'"""

            # Đưa thành phẩm vào danh sách mới
            ai_patches[cve_id] = {
                "summary": details.get("summary"),
                "poc_url": details.get("poc_url", "No PoC"),
                "patch_analysis": {
                    "status": "Patched_by_EvoNet_3B_V1",
                    "diff_code": generated_patch_code,
                    "mitigation_steps": mitigation
                }
            }
            
            processed_count += 1
            print(f"✅ Đã xử lý xong {cve_id}!")

    # 4. XUẤT RA ĐĨA MỚI (Lưu vào file bị Git bỏ qua)
    if processed_count > 0:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(ai_patches, f, indent=4, ensure_ascii=False)
        print(f"\n🚀 Đã lưu an toàn {processed_count} bản vá vào kho vũ khí Local!")
    else:
        print("\n✅ Tất cả các lỗ hổng đều đã được AI xử lý trước đó.")

if __name__ == "__main__":
    print("🧬 Kích hoạt Đặc vụ EvoNet-3B-V1 Patcher...")
    run_local_ai_patcher()