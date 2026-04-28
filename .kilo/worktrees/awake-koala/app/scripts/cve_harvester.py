import requests
import chromadb

print("🛡️ Đang khởi động Mắt Thần An Ninh EvoNet...")

# Kết nối thẳng vào container ChromaDB qua mạng nội bộ Docker
client = chromadb.HttpClient(host='evonet_vector_db', port=8000)

# Tạo một ngăn kéo trí nhớ mới tên là "security_cves"
collection = client.get_or_create_collection(name="security_cves")

print("📡 Đang kết nối Trạm thông tin NVD Quốc gia Mỹ...")
# Link lấy 5 lỗ hổng Zero-day mới nhất (không cần API Key để test)
url = "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=5"

headers = {
    "User-Agent": "EvoNet-Security-Agent/1.0"
}

try:
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    vulnerabilities = data.get("vulnerabilities", [])
    print(f"🔥 Phát hiện {len(vulnerabilities)} lỗ hổng mới. Đang tiến hành nạp vào não...")

    for item in vulnerabilities:
        cve = item["cve"]
        cve_id = cve["id"]
        # Lấy đoạn mô tả lỗi (thường ở vị trí đầu tiên)
        desc = cve["descriptions"][0]["value"]

        # Bơm thẳng vào ChromaDB
        collection.add(
            documents=[f"Lỗ hổng {cve_id}: {desc}"],
            metadatas=[{"source": "NVD", "type": "cve_alert"}],
            ids=[cve_id]
        )
        print(f"✅ Đã khắc ghi vào trí nhớ: {cve_id}")

    print("🎉 Hoàn tất! EvoNet đã cập nhật kiến thức bảo mật mới nhất.")

except Exception as e:
    print(f"❌ Thu thập thất bại. Nguyên nhân: {e}")
