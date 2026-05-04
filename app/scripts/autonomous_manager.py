import time
import subprocess
import requests
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)


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
    except Exception as e:
        print(f"Failed to send Telegram: {e}")


def run_script(script_name):
    print(f"[AUTONOMOUS] Running: {script_name}")
    try:
        result = subprocess.run(
            ["python3", f"app/scripts/{script_name}"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print(f"[AUTONOMOUS] Completed: {script_name}")
            return True
        else:
            print(f"[AUTONOMOUS] Error in {script_name}: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[AUTONOMOUS] Timeout: {script_name}")
        return False
    except Exception as e:
        print(f"[AUTONOMOUS] Error running {script_name}: {e}")
        return False


def health_check():
    try:
        response = requests.get("http://localhost:8080/v1/models", timeout=10)
        if response.status_code == 200:
            send_telegram("🏥 <b>HEALTH CHECK:</b>\nSystem operational")
        else:
            send_telegram("⚠️ <b>HEALTH CHECK:</b>\nSystem may be degraded")
    except Exception as e:
        send_telegram(f"❌ <b>HEALTH CHECK FAILED:</b>\n{e}")


def run_comprehensive_update():
    print("[AUTONOMOUS] Starting comprehensive update...")
    send_telegram("🔄 <b>COMPREHENSIVE UPDATE:</b> Starting update cycle...")
    scripts = [
        "threat_intel_collector.py",
        "cve_refinery.py",
        "self_evolve.py",
        "evo_autofix.py",
        "advanced_static_analyzer.py",
        "attack_simulator.py",
        "threat_alert_system.py",
    ]
    for script in scripts:
        run_script(script)
    send_telegram("✅ <b>COMPREHENSIVE UPDATE COMPLETE</b>")


def autonomous_system_monitor():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        if cpu > 80 or memory.percent > 80 or disk.percent > 90:
            status = f"CPU: {cpu}% | RAM: {memory.percent}% | Disk: {disk.percent}%"
            send_telegram(f"⚠️ <b>RESOURCE WARNING:</b>\n{status}")
    except ImportError:
        pass
    except Exception as e:
        print(f"System monitoring error: {e}")


def run_federated_learning():
    try:
        from federated_learning.fl_integration import periodic_fl_training
        periodic_fl_training()
        return True
    except Exception as e:
        print(f"FL error: {e}")
        return False


def run_continuous_learning():
    run_script("self_qa.py")
    run_script("code_harvester.py")
    return True


def run_security_assessment():
    run_script("vulnerability_scanner.py")
    run_script("red_team_simulator.py")
    return True


def run_incident_response():
    run_script("incident_response.py")
    return True


def run_bug_bounty_hunting():
    run_script("bug_bounty_hunter.py")
    return True


def main():
    jobstores = {'default': MemoryJobStore()}
    executors = {'default': ThreadPoolExecutor(20)}
    job_defaults = {'coalesce': False, 'max_instances': 3}

    scheduler = BackgroundScheduler(
        jobstores=jobstores, executors=executors, job_defaults=job_defaults
    )

    scheduler.add_job(health_check, 'interval', minutes=30, id='health_check')
    scheduler.add_job(lambda: run_script("cve_refinery.py"), 'interval', hours=1, id='cve_scan')
    scheduler.add_job(lambda: run_script("system_watchdog.py"), 'interval', hours=2, id='system_watchdog')
    scheduler.add_job(lambda: run_script("code_harvester.py"), 'interval', hours=3, id='code_harvest')
    scheduler.add_job(lambda: run_script("threat_intel_collector.py"), 'interval', hours=4, id='threat_collection')
    scheduler.add_job(lambda: run_script("self_evolve.py"), 'interval', hours=6, id='self_evolve')
    scheduler.add_job(lambda: run_script("advanced_static_analyzer.py"), 'interval', hours=8, id='advanced_analysis')
    scheduler.add_job(run_comprehensive_update, 'interval', hours=12, id='comprehensive_update')
    scheduler.add_job(run_federated_learning, 'interval', days=1, id='federated_learning')
    scheduler.add_job(autonomous_system_monitor, 'interval', minutes=30, id='system_monitor')
    scheduler.add_job(run_continuous_learning, 'interval', hours=5, id='continuous_learning')
    scheduler.add_job(run_security_assessment, 'interval', hours=6, id='security_assessment')
    scheduler.add_job(run_incident_response, 'interval', days=1, id='incident_response')
    scheduler.add_job(run_bug_bounty_hunting, 'interval', days=3, id='bug_bounty_hunting')

    print("EvoNet Autonomous Manager started. Running 24/7 evolution loop...")
    send_telegram("🟢 <b>AUTONOMOUS SYSTEM ACTIVE:</b> 24/7 evolution loop started")
    scheduler.start()

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down autonomous manager...")
        send_telegram("🔴 <b>AUTONOMOUS SYSTEM SHUTTING DOWN</b>")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
