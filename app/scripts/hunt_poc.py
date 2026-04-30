import json
import os
import requests
import time

DATA_FILE = "data/latest_threats.json"

def hunt_poc():
    if not os.path.exists(DATA_FILE):
        print("💤 Kho chứa trống rỗng. Chắc Bot 1 chưa cào được gì.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cves = json.load(f)

    updated = False
    for cve_id, details in cves.items():
        # Chỉ nhận việc nếu Bot 1 đã dán nhãn (tag) là hàng mới cào về
        if details.get("stage") == "1_CVE_Harvested":
            print(f"🥷 Đang sục sạo mạng lưới tìm PoC cho {cve_id}...")
            
            # Gọi API tìm kiếm của GitHub để tìm kho chứa PoC
            url = f"https://api.github.com/search/repositories?q={cve_id}+poc&sort=stars&order=desc"
            try:
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    items = res.json().get("items", [])
                    if items:
                        # Lấy cái PoC uy tín nhất (nhiều sao nhất)
                        poc_url = items[0].get("html_url")
                        details["poc_url"] = poc_url
                        details["stage"] = "2_PoC_Found" # Chuyển tag cho Bot 3
                        print(f"✅ Húp được mã khai thác: {poc_url}")
                        updated = True
                    else:
                        print(f"❌ Giang hồ chưa ai viết PoC cho lỗ hổng này.")
                        details["stage"] = "2_No_PoC" # Vẫn chuyển tag để đi tiếp
                        updated = True
            except Exception as e:
                print(f"❌ Đứt cáp: {e}")
            
            # Ngủ 3 giây giữa mỗi lần tìm để không bị GitHub chặn IP
            time.sleep(3) 

    if updated:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cves, f, indent=4, ensure_ascii=False)
        print("💾 Đã nạp thành công vũ khí (PoC) vào database!")

if __name__ == "__main__":
    print("🧬 Kích hoạt Đặc vụ EvoNet: PoC Hunter...")
    hunt_poc()