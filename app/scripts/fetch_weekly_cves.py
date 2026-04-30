import json
import os
import requests
from datetime import datetime

# Đường dẫn file lưu trữ trên GitHub
DATA_FILE = "data/latest_threats.json"

def fetch_latest_cves():
    """Cào 30 lỗ hổng CVE mới nhất từ CIRCL API (Miễn phí, không cần Key)"""
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

    # 2. Mở sổ tay dữ liệu cũ ra xem (Để lọc trùng lặp)
    existing_cves = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                existing_cves = json.load(f)
            except json.JSONDecodeError:
                existing_cves = {} # Nếu file rỗng hoặc lỗi thì tạo mới

    # 3. Lấy dữ liệu mới về
    new_data = fetch_latest_cves()
    added_count = 0

    # 4. BỘ LỌC CHÍ MẠNG: Chỉ lấy hàng mới, bỏ qua hàng cũ
    for item in new_data:
        cve_id = item.get("id")
        
        # Nếu ID này CHƯA TỪNG CÓ trong file JSON của sếp
        if cve_id and cve_id not in existing_cves:
            existing_cves[cve_id] = {
                "summary": item.get("summary", "Không có mô tả"),
                "cvss_score": item.get("cvss", "N/A"),
                "date_added_to_evonet": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            added_count += 1

    # 5. Lưu lại vào file nếu có "chiến lợi phẩm" mới
    if added_count > 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_cves, f, indent=4, ensure_ascii=False)
        print(f"✅ Đã tóm được và cập nhật {added_count} CVE mới vào hệ thống!")
    else:
        print("💤 Hôm nay giang hồ yên ả, không có CVE nào mới.")

if __name__ == "__main__":
    print("🧬 Kích hoạt EvoNet Threat Crawler...")
    update_cve_database()