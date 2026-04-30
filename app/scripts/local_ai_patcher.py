import json
import os

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

    # 3. KÍCH HOẠT AI CHẾ BIẾN (Tương lai sếp cắm API của Qwen vào đây)
    for cve_id, details in cves.items():
        # Chỉ xử lý những file đã được Bot 3 dán nhãn sẵn sàng
        if details.get("stage") == "3_Ready_for_Fine_Tuning" and cve_id not in ai_patches:
            print(f"🧠 Qwen đang phân tích lỗ hổng {cve_id}...")
            
            # GIẢ LẬP: Chỗ này AI sẽ suy nghĩ và sinh ra code
            generated_patch_code = "def fix_sql_injection():\n    return 'Sanitized Data'"
            mitigation = "Cập nhật thư viện lên bản mới nhất và lọc input đầu vào."

            # Đưa thành phẩm vào danh sách mới
            ai_patches[cve_id] = {
                "summary": details.get("summary"),
                "poc_url": details.get("poc_url", "No PoC"),
                "patch_analysis": {
                    "status": "Patched_by_EvoNet_Qwen",
                    "diff_code": generated_patch_code,
                    "mitigation_steps": mitigation
                }
            }
            processed_count += 1
            print(f"✅ Đã vá xong {cve_id}!")

    # 4. XUẤT RA ĐĨA MỚI (Lưu vào file bị Git bỏ qua)
    if processed_count > 0:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(ai_patches, f, indent=4, ensure_ascii=False)
        print(f"💾 Đã lưu an toàn {processed_count} bản vá vào kho vũ khí Local!")
    else:
        print("✅ Tất cả các lỗ hổng đều đã được AI xử lý trước đó.")

if __name__ == "__main__":
    print("🧬 Kích hoạt EvoNet Local AI Patcher...")
    run_local_ai_patcher()