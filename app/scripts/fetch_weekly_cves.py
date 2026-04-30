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

    # 4. BỘ LỌC CHÍ MẠNG KÉP: Hàng mới + Độ nguy hiểm cao
    for item in new_data:
        cve_id = item.get("id")
        cvss_score = item.get("cvss")
        
        # Kiểm tra xem có mã ID và chưa từng lưu trong hệ thống không
        if cve_id and cve_id not in existing_cves:
            # Kiểm tra xem có điểm số và điểm số phải >= 7.0
            if cvss_score is not None and float(cvss_score) >= 7.0:
                existing_cves[cve_id] = {
                    "summary": item.get("summary", "Không có mô tả"),
                    "cvss_score": float(cvss_score),
                    "date_added_to_evonet": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stage": "1_CVE_Harvested" # Gắn tag để Bot 2 biết đường vào nhận việc
                }
                added_count += 1
                print(f"⚠️ Báo động: Bắt được {cve_id} (Điểm CVSS: {cvss_score})")

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