import os
import time
import subprocess
import json
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/phong/evonet-core/.env", override=True)

def get_env_safe(key_name):
    val = os.getenv(key_name)
    if val:
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None

def send_telegram(msg):
    token = get_env_safe("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_safe("TELEGRAM_CHAT_ID")
    if not token or not chat_id: 
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try: 
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

class AutoUpdateSystem:
    """Fully automated update and patching system"""
    
    def __init__(self):
        self.workspace_path = Path("/workspace")
        self.scripts_path = Path("/app/scripts")
        self.last_run_file = Path("/app/logs/last_auto_run.json")
        
    def check_internet_connection(self) -> bool:
        """Check if internet connection is available"""
        try:
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_last_run_info(self) -> Dict:
        """Get information about the last auto run"""
        if self.last_run_file.exists():
            try:
                with open(self.last_run_file, "r") as f:
                    return json.load(f)
            except:
                pass
        
        # Default last run info
        return {
            "last_full_update": "1970-01-01T00:00:00",
            "last_threat_collection": "1970-01-01T00:00:00",
            "last_cve_collection": "1970-01-01T00:00:00",
            "last_self_evolve": "1970-01-01T00:00:00",
            "last_auto_fix": "1970-01-01T00:00:00"
        }
    
    def save_last_run_info(self, info: Dict):
        """Save information about the last auto run"""
        try:
            self.last_run_file.parent.mkdir(exist_ok=True)
            with open(self.last_run_file, "w") as f:
                json.dump(info, f, indent=2)
        except Exception as e:
            print(f"Error saving last run info: {e}")
    
    def should_run_full_update(self) -> bool:
        """Check if a full update should be run"""
        last_info = self.get_last_run_info()
        last_update = datetime.fromisoformat(last_info["last_full_update"])
        # Run full update every 24 hours
        return datetime.now() - last_update > timedelta(hours=24)
    
    def should_collect_threats(self) -> bool:
        """Check if threat collection should be run"""
        last_info = self.get_last_run_info()
        last_collection = datetime.fromisoformat(last_info["last_threat_collection"])
        # Collect threats every 6 hours
        return datetime.now() - last_collection > timedelta(hours=6)
    
    def should_collect_cves(self) -> bool:
        """Check if CVE collection should be run"""
        last_info = self.get_last_run_info()
        last_collection = datetime.fromisoformat(last_info["last_cve_collection"])
        # Collect CVEs every 12 hours
        return datetime.now() - last_collection > timedelta(hours=12)
    
    def should_self_evolve(self) -> bool:
        """Check if self evolution should be run"""
        last_info = self.get_last_run_info()
        last_evolution = datetime.fromisoformat(last_info["last_self_evolve"])
        # Self evolve every 24 hours
        return datetime.now() - last_evolution > timedelta(hours=24)
    
    def should_auto_fix(self) -> bool:
        """Check if auto fix should be run"""
        last_info = self.get_last_run_info()
        last_fix = datetime.fromisoformat(last_info["last_auto_fix"])
        # Auto fix every 6 hours
        return datetime.now() - last_fix > timedelta(hours=6)
    
    def run_threat_collection(self):
        """Run threat collection"""
        try:
            print("🤖 THU THẬP THÔNG TIN ĐE DỌA TỰ ĐỘNG: Đang thu thập dữ liệu từ các nguồn đe dọa...")
            # Set the PYTHONPATH environment variable
            env = os.environ.copy()
            env['PYTHONPATH'] = "/home/phong/evonet-core"
            
            # Change to the project directory and activate virtual environment
            cmd = f"cd /home/phong/evonet-core && . venv/bin/activate && PYTHONPATH=/home/phong/evonet-core:$PYTHONPATH python3 app/scripts/threat_intel_collector.py"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300, env=env, cwd="/home/phong/evonet-core", executable='/bin/bash')
            
            if result.returncode == 0:
                print("✅ THU THẬP THÔNG TIN ĐE DỌA TỰ ĐỘNG: Hoàn tất thu thập thông tin đe dọa")
                return True
            else:
                print(f"❌ THU THẬP THÔNG TIN ĐE DỌA TỰ ĐỘNG: Lỗi khi thu thập thông tin đe dọa {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ THU THẬP THÔNG TIN ĐE DỌA TỰ ĐỘNG: Lỗi hệ thống: {e}")
            return False
    
    def run_cve_collection(self):
        """Run CVE collection"""
        try:
            result = subprocess.run(["python3", str(self.scripts_path / "cve_refinery.py")], 
                                   capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            print(f"Error collecting CVEs: {e}")
            return False
    
    def run_self_evolution(self):
        """Run self evolution"""
        try:
            result = subprocess.run(["python3", str(self.scripts_path / "self_evolve.py")], 
                                  capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            print(f"Error in self evolution: {e}")
            return False
    
    def run_auto_fix(self):
        """Run auto fix"""
        try:
            # This would normally check for actual errors, but for demo we'll just run the script
            result = subprocess.run(["python3", str(self.scripts_path / "evo_autofix.py")], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            print(f"Error in auto fix: {e}")
            return False
    
    def run_full_update_cycle(self):
        """Run the full update cycle"""
        try:
            # Update last run info
            last_info = self.get_last_run_info()
            
            # Run threat collection
            if self.should_collect_threats():
                if self.run_threat_collection():
                    last_info["last_threat_collection"] = datetime.now().isoformat()
            
            # Run CVE collection
            if self.should_collect_cves():
                if self.run_cve_collection():
                    last_info["last_cve_collection"] = datetime.now().isoformat()
            
            # Run self evolution
            if self.should_self_evolve():
                if self.run_self_evolution():
                    last_info["last_self_evolve"] = datetime.now().isoformat()
            
            # Run auto fix
            if self.should_auto_fix():
                if self.run_auto_fix():
                    last_info["last_auto_fix"] = datetime.now().isoformat()
            
            # Update last full update time
            last_info["last_full_update"] = datetime.now().isoformat()
            
            # Save updated info
            self.save_last_run_info(last_info)
            
        except Exception as e:
            print(f"Error in update cycle: {e}")
    
    def start_scheduler(self):
        """Start the automated scheduler"""
        # Schedule the full update cycle to run every 6 hours
        schedule.every(6).hours.do(self.run_full_update_cycle)
        
        # Also run once immediately on startup
        self.run_full_update_cycle()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main function to start the auto update system"""
    print("Starting auto update system...")
    
    # Create auto update system instance
    auto_system = AutoUpdateSystem()
    
    # Check internet connection
    if not auto_system.check_internet_connection():
        print("No internet connection, exiting...")
        return
    
    # Start the scheduler
    auto_system.start_scheduler()

if __name__ == "__main__":
    main()