import json
import os

DATA_FILE = "data/latest_threats.json"

def analyze_patch():
    if not os.path.exists(DATA_FILE):
        print("💤 Không có dữ liệu để phân tích.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cves = json.load(f)

    updated = False
    for cve_id, details in cves.items():
        # Chỉ xử lý những lỗ hổng đã qua tay Bot 2
        if details.get("stage") in ["2_PoC_Found", "2_No_PoC"]:
            print(f"🛡️ Đang đóng gói dữ liệu bản vá cho {cve_id}...")
            
            # Xây dựng cấu trúc (Schema) chuẩn bị cho Model LLM Fine-tuning
            details["patch_analysis"] = {
                "status": "Ready_for_LLM",
                "diff_code": "To_be_generated", # Chỗ này model sẽ tự sinh ra code vá lỗi
                "mitigation_steps": "To_be_generated"
            }
            # Gắn mác chốt sổ để xuất xưởng
            details["stage"] = "3_Ready_for_Fine_Tuning"
            updated = True
            print(f"✅ Đã dán nhãn xuất xưởng cho {cve_id}!")

    if updated:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cves, f, indent=4, ensure_ascii=False)
        print("💾 Băng chuyền hoàn tất! Bộ dữ liệu Training đã sẵn sàng!")

if __name__ == "__main__":
    print("🧬 Kích hoạt Đặc vụ EvoNet: Patch Analyzer...")
    analyze_patch()