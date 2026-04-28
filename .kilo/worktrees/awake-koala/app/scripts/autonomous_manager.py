import time
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler

def run_script(script_name):
    print(f"🚀 [AUTONOMOUS] Kích hoạt: {script_name}")
    try:
        # Chạy script như một tiến trình riêng
        subprocess.run(["python", f"scripts/{script_name}"], check=True)
    except Exception as e:
        print(f"❌ [AUTONOMOUS] Lỗi khi chạy {script_name}: {e}")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()

    # --- THIẾT LẬP VÒNG LẶP TIẾN HÓA LIÊN TỤC ---
    
    # 1. Mỗi 1 tiếng: Mắt thần đi quét lỗ hổng CVE mới
    scheduler.add_job(lambda: run_script("cve_refinery.py"), 'interval', hours=1)
    
    # 2. Mỗi 1 tiếng: Watchdog quét hệ thống và kích hoạt vá lỗi/tự học
    scheduler.add_job(lambda: run_script("system_watchdog.py"), 'interval', hours=1)
    
    # 3. Mỗi 2 tiếng: AI tự "nằm mơ" đẻ ra bài học Q&A mới
    scheduler.add_job(lambda: run_script("self_qa.py"), 'interval', hours=2)
    
    # 4. Mỗi 3 tiếng: Cánh tay Robot gom code nội bộ (nếu sếp có cập nhật code mới)
    scheduler.add_job(lambda: run_script("code_harvester.py"), 'interval', hours=3)

    print("🤖 EvoNet Autonomous Manager đã sẵn sàng. Bắt đầu vòng lặp tiến hóa...")
    scheduler.start()

    try:
        # Giữ cho script luôn chạy ngầm bên trong Docker
        while True:
            time.sleep(100)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
