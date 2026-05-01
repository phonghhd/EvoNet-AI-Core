import json
import os
import requests
from datetime import datetime

# Đường dẫn file lưu trữ trên GitHub
DATA_FILE = "data/latest_threats.json"

def fetch_latest_cves():
    """Cào 30 lỗ hổng CVE mới nhất từ CIRCL API"""
    print("📡 Đang kết nối tới trung tâm dữ liệu CVE...")
    url = "https://cve.circl.lu/api/last"
    try:
        response = requests.get(url, timeout=15)
        return response.json()
    except Exception as e:
        print(f"❌ Lỗi mạng khi cào dữ liệu: {e}")
        return []

def update_cve_database():
    # 1. Tạo thư mục data/ nếu chưa có
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    # 2. Mở sổ tay dữ liệu cũ ra xem
    existing_cves = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                existing_cves = json.load(f)
            except json.JSONDecodeError:
                existing_cves = {}

    # 3. Lấy dữ liệu mới về
    new_data = fetch_latest_cves()
    added_count = 0

    print("🔍 Đang khởi động bộ lọc CVSS >= 7.0 (High/Critical)...")

    # 4. BỘ LỌC THÔNG MINH VÀ TỰ ĐỘNG DỌN RÁC (Garbage Collection)
    for item in new_data:
        cve_id = item.get("id")
        cvss_score = item.get("cvss")
        
        # --- TÍNH NĂNG 1: QUẢN LÝ HỒ SƠ CŨ (DỌN RÁC) ---
        if cve_id in existing_cves:
            # Nếu lúc trước lưu tạm vì chưa có điểm, nay API đã nhả điểm chính thức
            if existing_cves[cve_id].get("cvss_score") == "Chưa chấm điểm (Có biến!)" and cvss_score is not None:
                official_score = float(cvss_score)
                if official_score < 7.0:
                    # Điểm thấp -> Rác -> XÓA KHỎI BỘ NHỚ NGAY VÀ LUÔN
                    del existing_cves[cve_id]
                    print(f"🗑️ Đã ném {cve_id} vào thùng rác vì điểm chính thức quá bèo ({official_score}).")
                else:
                    # Điểm cao -> Cập nhật con số chính thức vào hồ sơ
                    existing_cves[cve_id]["cvss_score"] = official_score
                    print(f"🔥 Cập nhật {cve_id}: Quái vật đã lộ diện với điểm chính thức ({official_score}).")
            
            # Xử lý xong hồ sơ cũ thì bỏ qua vòng lặp này để đi tới lỗ hổng tiếp theo
            continue 

        # --- TÍNH NĂNG 2: SĂN LÙNG MỒI MỚI TOANH ---
        # TH1: Đã có điểm và >= 7.0 (High/Critical)
        is_high_risk = cvss_score is not None and float(cvss_score) >= 7.0
        
        # TH2: Mới toanh chưa có điểm (Báo động ngầm, bắt về chờ xét xử)
        is_unscored_new = cvss_score is None
        
        if is_high_risk or is_unscored_new:
            score_display = float(cvss_score) if cvss_score else "Chưa chấm điểm (Có biến!)"
            existing_cves[cve_id] = {
                "summary": item.get("summary", "Không có mô tả"),
                "cvss_score": score_display,
                "date_added_to_evonet": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stage": "1_CVE_Harvested" 
            }
            added_count += 1
            print(f"⚠️ Đã tóm mồi mới: {cve_id} - Điểm: {score_display}")

    # 5. LUÔN LUÔN LƯU FILE (Để giữ băng chuyền Pipeline không bị đứt)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_cves, f, indent=4, ensure_ascii=False)

    if added_count > 0:
        print(f"✅ Đã tóm được {added_count} CVE NGUY HIỂM vào danh sách chờ xử lý!")
    else:
        print("💤 Không có lỗ hổng NGUY HIỂM nào xuất hiện. Vẫn giao lại hồ sơ cũ cho Bot 2!")

if __name__ == "__main__":
    print("🧬 Kích hoạt EvoNet Threat Harvester (Phiên bản Lọc Nguy Hiểm)...")
    update_cve_database()