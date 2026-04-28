import os
import requests
from github import Github
import datetime

# --- CẤU HÌNH BIẾN ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # Sếp cần tạo trên GitHub
REPO_NAME = os.getenv("GITHUB_REPO") # Ví dụ: "phonghuynh/evonet-core"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def ask_nvidia_to_fix(error_log, file_content):
    """Giao file lỗi và log lỗi cho Nvidia NIM để nó tự viết lại code"""
    print("🧠 Gọi Kỹ sư Trưởng Nvidia phân tích lỗi...")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""
    Hệ thống vừa sập. Dưới đây là Log lỗi:
    {error_log}
    
    Và đây là nội dung file code hiện tại:
    ```python
    {file_content}
    ```
    
    Hãy tìm ra nguyên nhân và TRẢ VỀ TOÀN BỘ ĐOẠN CODE ĐÃ ĐƯỢC VÁ LỖI. 
    Lưu ý: Chỉ trả về code thuần, KHÔNG giải thích lằng nhằng, KHÔNG dùng markdown ```python, để tôi có thể ghi thẳng vào file.
    """
    
    payload = {
        "model": "nvidia/nemotron-4-340b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1 # Tránh việc AI sáng tạo quá đà làm sai logic code
    }
    
    res = requests.post(url, headers=headers, json=payload)
    return res.json()["choices"][0]["message"]["content"].strip()

def create_auto_fix_pr(file_path, error_log):
    """Tự động tạo nhánh mới và mở Pull Request trên GitHub"""
    if not GITHUB_TOKEN or not REPO_NAME:
        print("❌ Thiếu Token GitHub hoặc Tên Repo!")
        return

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    try:
        # 1. Lấy nội dung file hiện tại trên GitHub
        file_contents = repo.get_contents(file_path, ref="main")
        current_code = file_contents.decoded_content.decode("utf-8")
        
        # 2. Gọi Nvidia NIM vá lỗi
        fixed_code = ask_nvidia_to_fix(error_log, current_code)
        
        # 3. Tạo nhánh mới (Branch)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_branch = f"evo-autofix-{timestamp}"
        main_branch = repo.get_branch("main")
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=main_branch.commit.sha)
        
        # 4. Ghi đè code đã vá lên nhánh mới
        commit_msg = f"🤖 Tiêm kháng thể vá lỗi hệ thống tự động ({timestamp})"
        repo.update_file(file_contents.path, commit_msg, fixed_code, file_contents.sha, branch=new_branch)
        
        # 5. Mở Pull Request
        pr_title = f"🚑 Evo-AutoFix: Đề xuất vá lỗi cho `{file_path}`"
        pr_body = f"**Hệ thống phát hiện lỗi:**\n```\n{error_log}\n```\n\nNvidia NIM đã phân tích và tự động đưa ra bản vá này. Sếp Phong vui lòng review!"
        pr = repo.create_pull(title=pr_title, body=pr_body, head=new_branch, base="main")
        
        # 6. Báo cáo cho sếp
        alert_msg = f"🚨 <b>HỆ THỐNG GẶP SỰ CỐ NHƯNG ĐÃ ĐƯỢC XỬ LÝ!</b>\n\n📁 <b>File lỗi:</b> {file_path}\n🧠 <b>AI Vá lỗi:</b> Nvidia NIM\n🔗 <b>Link Phê duyệt (PR):</b> {pr.html_url}\n\nSếp Phong hãy click vào link để kiểm tra code và bấm Merge nhé!"
        send_telegram(alert_msg)
        print("✅ Đã tiêm kháng thể thành công!")
        
    except Exception as e:
        send_telegram(f"❌ <b>Evo-AutoFix Thất bại:</b>\nKhông thể vá file {file_path}. Lỗi nội bộ: {e}")

# Chạy test giả lập
if __name__ == "__main__":
    # Giả lập một lỗi chia cho 0 trong file main.py
    fake_error = "ZeroDivisionError: division by zero at line 42 in ask_api()"
    # Chỉ gọi hàm khi sếp đã cấu hình xong Repo
    # create_auto_fix_pr("app/main.py", fake_error)
