#!/usr/bin/env python3
"""EvoNet-Core: Autonomous AI Security Agent - Complete System Startup"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path
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
    except Exception:
        pass


def check_docker_compose():
    try:
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def start_docker_services():
    send_telegram("🐳 Starting Docker services...")
    result = subprocess.run(["docker-compose", "up", "-d"], capture_output=True, text=True)
    if result.returncode == 0:
        send_telegram("✅ Docker services started")
        return True
    send_telegram(f"❌ Docker error: {result.stderr}")
    return False


def check_health(url, name, retries=5, delay=10):
    for i in range(retries):
        try:
            if requests.get(url, timeout=10).status_code == 200:
                return True
        except Exception:
            pass
        print(f"Waiting for {name}... ({i+1}/{retries})")
        time.sleep(delay)
    return False


def run_initial_setup():
    send_telegram("⚙️ Running initial setup...")
    scripts = [
        ("threat_intel_collector.py", "Threat Intel"),
        ("cve_refinery.py", "CVE Collection"),
        ("self_evolve.py", "Self-Evolution"),
    ]
    for script, name in scripts:
        print(f"Running {name}...")
        try:
            subprocess.run(["python", f"app/scripts/{script}"], capture_output=True, text=True, timeout=600)
        except Exception as e:
            print(f"{name} error: {e}")
    send_telegram("✅ Initial setup complete")


def main():
    print("EvoNet-Core starting...")
    send_telegram("🚀 <b>EVONET-CORE:</b> Starting autonomous security system...")

    if not check_docker_compose():
        print("docker-compose not available")
        send_telegram("⚠️ Please install Docker and docker-compose")
        return

    if not start_docker_services():
        return

    print("Waiting for services...")
    time.sleep(15)

    if not check_health("http://localhost:8080/v1/models", "API"):
        send_telegram("⚠️ API not responding")
        return

    if not check_health("http://localhost:8081", "Dashboard"):
        send_telegram("⚠️ Dashboard not responding")

    run_initial_setup()

    subprocess.Popen(["python", "app/scripts/auto_update_system.py"])

    send_telegram("✅ <b>EVONET-CORE READY</b>")
    send_telegram("🌐 Dashboard: http://localhost:8081")
    send_telegram("📱 Control via Telegram bot")

    print("System running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down...")
        send_telegram("🔴 <b>EVONET-CORE SHUTTING DOWN</b>")
        subprocess.run(["docker-compose", "down"])


if __name__ == "__main__":
    main()
