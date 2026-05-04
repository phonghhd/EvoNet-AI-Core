import os
import requests
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

def ask_ai_with_failover(system_prompt, user_prompt):
    """Hàm lõi: Gọi AI với cơ chế dự phòng 3 lớp"""
    
    # Lớp 1: Tiền đạo Groq (Tốc độ ánh sáng)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("🚀 Đang nhờ Tiền đạo Groq phân tích...")
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={"model": "llama3-70b-8192", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.1},
                timeout=10
            )
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            print(f"⚠️ Groq thất bại (Code: {res.status_code}). Chuyển quyền!")
        except Exception as e:
            print(f"⚠️ Groq sập nguồn: {e}")

    # Lớp 2: Trung vệ Nvidia (Sức mạnh tính toán)
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        print("🛡️ Đang gọi Trung vệ Nvidia ứng cứu...")
        try:
            res = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions", # Endpoint OpenAI tương thích của Nvidia
                headers={"Authorization": f"Bearer {nvidia_key}"},
                json={"model": "meta/llama3-70b-instruct", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.1},
                timeout=15
            )
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            print(f"⚠️ Nvidia thất bại (Code: {res.status_code}). Chuyển quyền!")
        except Exception as e:
            print(f"⚠️ Nvidia sập nguồn: {e}")

    # Lớp 3: Thủ môn Cloudflare Workers AI (Vững như bàn thạch)
    cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    cf_api_key = os.getenv("CLOUDFLARE_API_KEY")
    if cf_account_id and cf_api_key:
        print("🧱 Đang nhờ Thủ môn Cloudflare chốt chặn...")
        try:
            res = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/run/@cf/meta/llama-3-8b-instruct",
                headers={"Authorization": f"Bearer {cf_api_key}"},
                json={"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]},
                timeout=15
            )
            if res.status_code == 200:
                return res.json()["result"]["response"]
        except Exception as e:
            print(f"⚠️ Cloudflare sập nguồn: {e}")

    # Nếu cả 3 đều sụp (Trường hợp tận thế)
    return "VULNERABLE: Hệ thống AI giám sát đang gặp sự cố mạng diện rộng. Tạm thời khóa mã nguồn để đảm bảo an toàn tuyệt đối!"

@app.post("/api/v1/scan")
async def scan_code(payload: ScanPayload):
    print(f"📡 Nhận tín hiệu cầu cứu từ repo: {payload.repo} | Nhánh: {payload.branch}")
    
    system_prompt = """Bạn là EvoNet Guardian. Rà soát đoạn mã Git Diff. Phát hiện mã độc/lỗ hổng (như RCE, SQLi, lộ secret) thì trả lời bắt đầu bằng 'VULNERABLE:'. Nếu an toàn thì trả lời bắt đầu bằng 'SAFE:'."""
    user_prompt = f"Kiểm tra đoạn mã sau:\n\n{payload.code_diff}"

    # Gọi hàm 3 lớp
    ai_reply = ask_ai_with_failover(system_prompt, user_prompt)
    print(f"🤖 Phán quyết cuối cùng: {ai_reply}")

    if "VULNERABLE" in ai_reply.upper():
        return {"status": "VULNERABILITY_FOUND", "message": f"EvoNet AI đã chặn mã nguồn! Lý do: {ai_reply}"}
    else:
        return {"status": "SAFE", "message": f"EvoNet AI xác nhận an toàn: {ai_reply}"}

# Endpoint để kiểm tra server có đang sống không
@app.get("/")
def read_root():
    return {"status": "online", "message": "EvoNet AI Core Server đang trực chiến!"}

if __name__ == "__main__":
    # Khởi động server tại cổng 8000
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
