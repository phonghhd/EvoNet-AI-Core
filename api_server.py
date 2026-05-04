import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from github import Github

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
    file_path: str

def post_github_comment(repo_name, commit_sha, comment_body):
    """Hàm giúp EvoNet Bot chui vào GitHub để lại comment"""
    github_token = os.getenv("GITHUB_BOT_TOKEN")
    if not github_token:
        print("⚠️ Thiếu GITHUB_BOT_TOKEN, Bot không thể comment!")
        return

    # Sếp đang đẩy repo_name là "vietnamese-ai", cần ghép thêm tên tài khoản phonghhd của sếp vào
    full_repo = f"phonghhd/{repo_name}"
    
    # URL API của GitHub để comment thẳng vào cái commit bị lỗi
    url = f"https://api.github.com/repos/{full_repo}/commits/{commit_sha}/comments"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Nội dung comment Bot sẽ viết
    data = {
        "body": f"### 🛡️ EvoNet Security Bot Cảnh Báo\n\n**Phát hiện mã nguồn có vấn đề:**\n{comment_body}"
    }
    
    try:
        print("✍️ Đang cử Bot EvoNet lên GitHub để lại lời nhắn...")
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 201:
            print("✅ Bot EvoNet đã comment thành công!")
        else:
            print(f"❌ Lỗi comment GitHub: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối GitHub API: {e}")

def create_auto_pr(repo_name, commit_sha, file_path, patched_code):
    """Tuyệt kỹ: Bot chui vào GitHub tạo nhánh và mở Pull Request"""
    github_token = os.getenv("GITHUB_BOT_TOKEN")
    if not github_token:
        print("⚠️ Thiếu GITHUB_BOT_TOKEN, không thể tạo PR!")
        return

    try:
        print(f"🛠️ Đang khởi tạo Auto-Patching cho file {file_path}...")
        
        # 1. Đăng nhập vào GitHub
        g = Github(github_token)
        repo = g.get_repo(f"phonghhd/{repo_name}")
        
        # 2. Tạo tên nhánh mới dựa trên mã SHA của commit lỗi
        new_branch_name = f"evonet-patch-{commit_sha[:7]}"
        main_branch = repo.get_branch("main")
        
        # Tạo nhánh mới rẽ ra từ main
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=main_branch.commit.sha)
        
        # 3. Lấy file hiện tại để ghi đè
        file_contents = repo.get_contents(file_path, ref="main")
        
        # 4. Ghi đè đoạn code đã được AI vá lỗi lên nhánh mới
        repo.update_file(
            path=file_path,
            message=f"🛡️ EvoNet Auto-Patch: Vá lỗ hổng bảo mật",
            content=patched_code,
            sha=file_contents.sha,
            branch=new_branch_name
        )
        
        # 5. Mở Pull Request dâng lên cho Sếp Phong duyệt
        pr = repo.create_pull(
            title=f"[EvoNet Bot] 🛡️ Đề xuất vá lỗi bảo mật khẩn cấp",
            body="EvoNet AI Guardian đã phát hiện lỗ hổng. Máy chủ đã tự động viết lại mã nguồn an toàn. Sếp kiểm tra và Merge nhé! 🚀",
            head=new_branch_name,
            base="main"
        )
        print(f"✅ ĐẠI CÔNG CÁO THÀNH! PR đã tạo tại: {pr.html_url}")

    except Exception as e:
        print(f"❌ Khởi tạo Auto-PR thất bại: {e}")

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
    
    system_prompt = """Bạn là EvoNet Guardian. Rà soát đoạn mã Git Diff. 
    Nếu phát hiện mã độc/lỗ hổng, hãy TRẢ VỀ TOÀN BỘ ĐOẠN MÃ ĐÃ ĐƯỢC VÁ LỖI. 
    YÊU CẦU TỐI THƯỢNG: Chỉ trả về mã nguồn thuần túy, tuyệt đối không giải thích, không dùng markdown ```python, không có lời chào. 
    Nếu an toàn, hãy trả lời đúng 1 chữ: 'SAFE'."""
    user_prompt = f"Kiểm tra đoạn mã sau:\n\n{payload.code_diff}"

    # Gọi hàm 3 lớp
    ai_reply = ask_ai_with_failover(system_prompt, user_prompt)
    print(f"🤖 Phán quyết cuối cùng: {ai_reply}")

    if ai_reply.strip() != "SAFE":
        # Gọi tuyệt kỹ Auto PR
        # Tạm thời gán file_path cứng để test, sau này sếp sẽ lấy từ GitHub Actions sang
        create_auto_pr(payload.repo, payload.commit_sha, payload.file_path, ai_reply)
        
        return {"status": "VULNERABILITY_FOUND", "message": "EvoNet AI đã chặn và tự động mở Pull Request vá lỗi!"}
    else:
        return {"status": "SAFE", "message": "Mã nguồn an toàn!"}
    
    

# Endpoint để kiểm tra server có đang sống không
@app.get("/")
def read_root():
    return {"status": "online", "message": "EvoNet AI Core Server đang trực chiến!"}

if __name__ == "__main__":
    # Khởi động server tại cổng 8000
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
