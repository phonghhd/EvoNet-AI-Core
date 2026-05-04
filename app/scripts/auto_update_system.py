import os
import time
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
import requests
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "app" / "scripts"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
LAST_RUN_FILE = LOGS_DIR / "last_auto_run.json"


def get_env_safe(key_name):
    val = os.getenv(key_name)
    if val:
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None


def send_telegram(msg):
    token = get_env_safe("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_safe("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception:
        pass


def run_script(script_name, timeout=300):
    script_path = SCRIPTS_DIR / script_name
    try:
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(PROJECT_ROOT), env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False


class AutoUpdateSystem:
    def __init__(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def get_last_run_info(self) -> Dict:
        if LAST_RUN_FILE.exists():
            try:
                with open(LAST_RUN_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {k: "1970-01-01T00:00:00" for k in [
            "last_full_update", "last_threat_collection",
            "last_cve_collection", "last_self_evolve", "last_auto_fix"
        ]}

    def save_last_run_info(self, info: Dict):
        with open(LAST_RUN_FILE, "w") as f:
            json.dump(info, f, indent=2)

    def should_run(self, key, hours):
        last = datetime.fromisoformat(self.get_last_run_info().get(key, "1970-01-01T00:00:00"))
        return datetime.now() - last > timedelta(hours=hours)

    def run_cycle(self):
        info = self.get_last_run_info()

        if self.should_run("last_threat_collection", 6):
            if run_script("threat_intel_collector.py"):
                info["last_threat_collection"] = datetime.now().isoformat()

        if self.should_run("last_cve_collection", 12):
            if run_script("cve_refinery.py"):
                info["last_cve_collection"] = datetime.now().isoformat()

        if self.should_run("last_self_evolve", 24):
            if run_script("self_evolve.py", timeout=600):
                info["last_self_evolve"] = datetime.now().isoformat()

        if self.should_run("last_auto_fix", 6):
            if run_script("evo_autofix.py"):
                info["last_auto_fix"] = datetime.now().isoformat()

        info["last_full_update"] = datetime.now().isoformat()
        self.save_last_run_info(info)

    def start_scheduler(self):
        try:
            import schedule
        except ImportError:
            subprocess.run(["pip3", "install", "schedule", "-q"])
            import schedule

        schedule.every(6).hours.do(self.run_cycle)
        self.run_cycle()

        print("Auto-update scheduler started (every 6h)")
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    print("Starting auto update system...")
    auto_system = AutoUpdateSystem()
    auto_system.start_scheduler()


if __name__ == "__main__":
    main()
