from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="EvoNet AI Core Security Shield",
    description="Trung tâm tiếp nhận và rà quét mã nguồn tự động",
    version="1.0"
)

# Khai báo cấu trúc dữ liệu mà vietnamese-ai sẽ gửi sang
class ScanPayload(BaseModel):
    repo: str
    branch: str
    commit_sha: str
    code_diff: str

# Cánh cổng (Endpoint) để nhận mã nguồn
@app.post("/api/v1/scan")
async def scan_code(payload: ScanPayload):
    print(f"📡 Nhận tín hiệu cầu cứu từ repo: {payload.repo} | Nhánh: {payload.branch}")
    print(f"🔍 Đang rà quét commit: {payload.commit_sha}")
    
    # ---------------------------------------------------------
    # TẠI ĐÂY SẼ LÀ NƠI SẾP GỌI NVIDIA/GROQ LLM SAU NÀY
    # Tạm thời anh em dùng Mock logic để test đường ống trước:
    # ---------------------------------------------------------
    
    # Giả sử phát hiện ai đó lén dùng hàm eval() nguy hiểm
    if "eval(" in payload.code_diff:
        print("❌ CẢNH BÁO: Phát hiện mã độc RCE!")
        return {
            "status": "VULNERABILITY_FOUND",
            "risk_level": "High",
            "message": "Phát hiện nguy cơ Code Injection (RCE) do sử dụng hàm eval(). Lệnh hợp nhất (Merge) bị từ chối."
        }
    
    # Nếu code sạch sẽ
    print("✅ Mã nguồn sạch sẽ, cho phép thông qua!")
    return {
        "status": "SAFE",
        "message": "EvoNet AI xác nhận mã nguồn an toàn!"
    }

# Endpoint để kiểm tra server có đang sống không
@app.get("/")
def read_root():
    return {"status": "online", "message": "EvoNet AI Core Server đang trực chiến!"}

if __name__ == "__main__":
    # Khởi động server tại cổng 8000
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)