import os
import sys
import requests
from github import Github
import datetime
import tempfile
import subprocess
from pathlib import Path
from patch_tester import PatchTester
from multi_language_support import MultiLanguageSupport
from dotenv import load_dotenv
load_dotenv("/app/.env", override=True)

# --- CẤU HÌNH BIẾN ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # Sếp cần tạo trên GitHub
REPO_NAME = os.getenv("GITHUB_REPO") # Ví dụ: "phonghuynh/evonet-core"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
AUTO_TEST_ENABLED = os.getenv("AUTO_TEST_ENABLED", "true").lower() == "true"

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def ask_nvidia_to_fix(error_log, file_content, iteration=1):
    """Giao file lỗi và log lỗi cho Nvidia NIM để nó tự viết lại code"""
    print(f"🧠 Gọi Kỹ sư Trưởng Nvidia phân tích lỗi (lần {iteration})...")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    
    # Detect language from file content or error log
    mls = MultiLanguageSupport()
    language = "python"  # Default
    
    # Try to detect language from file extensions
    # This is a simplified approach - in practice, you might want to pass the file path
    if "java" in error_log.lower() or ".java" in error_log:
        language = "java"
    elif "javascript" in error_log.lower() or ".js" in error_log:
        language = "javascript"
    elif ".ts" in error_log:
        language = "typescript"
    elif ".cpp" in error_log or ".cc" in error_log or ".cxx" in error_log:
        language = "cpp"
    elif ".cs" in error_log:
        language = "csharp"
    elif ".go" in error_log:
        language = "go"
    elif ".rs" in error_log:
        language = "rust"
    elif ".php" in error_log:
        language = "php"
    elif ".rb" in error_log:
        language = "ruby"
    elif ".swift" in error_log:
        language = "swift"
    elif ".kt" in error_log:
        language = "kotlin"
    
    language_names = {
        "python": "Python",
        "javascript": "JavaScript/Node.js",
        "typescript": "TypeScript",
        "java": "Java",
        "c": "C",
        "cpp": "C++",
        "csharp": "C#",
        "go": "Go",
        "rust": "Rust",
        "php": "PHP",
        "ruby": "Ruby",
        "swift": "Swift",
        "kotlin": "Kotlin"
    }
    
    language_name = language_names.get(language, "Python")
    
    # Modify prompt based on iteration
    if iteration == 1:
        prompt = f"""
        Hệ thống vừa sập. Dưới đây là Log lỗi:
        {error_log}
        
        Và đây là nội dung file code hiện tại:
        ```{language}
        {file_content}
        ```
        
        Hãy tìm ra nguyên nhân và TRẢ VỀ TOÀN BỘ ĐOẠN CODE ĐÃ ĐƯỢC VÁ LỖI. 
        Lưu ý: Chỉ trả về code thuần, KHÔNG giải thích lằng nhằng, KHÔNG dùng markdown ```{language}, để tôi có thể ghi thẳng vào file.
        Ngôn ngữ lập trình: {language_name}
        """
    else:
        # For subsequent iterations, include feedback about previous failures
        prompt = f"""
        Lần trước code vá của bạn đã không vượt qua kiểm thử. Dưới đây là log lỗi:
        {error_log}
        
        Nội dung file code hiện tại:
        ```{language}
        {file_content}
        ```
        
        Hãy tìm ra nguyên nhân và TRẢ VỀ TOÀN BỘ ĐOẠN CODE ĐÃ ĐƯỢC VÁ LỖI. 
        LƯU Ý: Code phải có thể chạy được và vượt qua kiểm thử tự động.
        Chỉ trả về code thuần, KHÔNG giải thích lằng nhằng, KHÔNG dùng markdown ```{language}.
        Ngôn ngữ lập trình: {language_name}
        """
    
    payload = {
        "model": "nvidia/nemotron-4-340b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1 if iteration == 1 else 0.05  # Even more conservative on retries
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=120)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"❌ Lỗi gọi API Nvidia: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"❌ Lỗi mạng khi gọi Nvidia: {e}")
        return None

def create_auto_fix_pr(file_path, error_log, max_iterations=3):
    """Tự động tạo nhánh mới và mở Pull Request trên GitHub với kiểm thử tự động"""
    if not GITHUB_TOKEN or not REPO_NAME:
        print("❌ Thiếu Token GitHub hoặc Tên Repo!")
        send_telegram("❌ <b>Evo-AutoFix Thất bại:</b>\nThiếu Token GitHub hoặc Tên Repo!")
        return

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    try:
        # 1. Lấy nội dung file hiện tại trên GitHub
        file_contents = repo.get_contents(file_path, ref="main")
        current_code = file_contents.decoded_content.decode("utf-8")
        
        # 2. Gọi Nvidia NIM vá lỗi (với nhiều lần thử nếu cần)
        fixed_code = None
        tester = PatchTester()
        
        for iteration in range(1, max_iterations + 1):
            print(f"🔄 Vòng lặp vá lỗi lần {iteration}/{max_iterations}")
            
            # Try to get a fix
            fixed_code = ask_nvidia_to_fix(error_log, current_code, iteration)
            if not fixed_code:
                send_telegram(f"❌ <b>Evo-AutoFix Thất bại:</b>\nKhông thể tạo bản vá từ Nvidia NIM")
                return
            
            # If auto-testing is disabled, break after first attempt
            if not AUTO_TEST_ENABLED:
                print("⏭️ Bỏ qua kiểm thử tự động theo cấu hình")
                break
                
            # Test the patch if auto-testing is enabled
            if AUTO_TEST_ENABLED:
                print("🧪 Đang kiểm thử bản vá...")
                test_result = tester.apply_patch_and_test(
                    original_file_path=Path(file_path),
                    patched_content=fixed_code
                )
                
                if test_result['patch_accepted']:
                    print("✅ Bản vá vượt qua kiểm thử!")
                    send_telegram("✅ <b>Evo-AutoFix:</b> Bản vá đã vượt qua kiểm thử tự động")
                    break
                else:
                    print(f"❌ Bản vá không vượt qua kiểm thử (lần {iteration})")
                    error_msg = test_result.get('stderr', 'Kiểm thử thất bại')
                    send_telegram(f"⚠️ <b>Evo-AutoFix:</b> Bản vá lần {iteration} không vượt qua kiểm thử: {error_msg}")
                    # Continue to next iteration to try again
                    if iteration == max_iterations:
                        send_telegram(f"❌ <b>Evo-AutoFix:</b> Không thể tạo bản vá hợp lệ sau {max_iterations} lần thử")
                        return
            else:
                # If testing is disabled, break after first attempt
                break
        
        if not fixed_code:
            send_telegram("❌ <b>Evo-AutoFix Thất bại:</b>\nKhông thể tạo bản vá hợp lệ!")
            return
            
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
        alert_msg = f"✅ <b>Evo-AutoFix THÀNH CÔNG!</b>\n\n📁 <b>File lỗi:</b> {file_path}\n🧠 <b>AI Vá lỗi:</b> Nvidia NIM\n🔗 <b>Link Phê duyệt (PR):</b> {pr.html_url}\n\nSếp Phong hãy click vào link để kiểm tra code và bấm Merge nhé!"
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