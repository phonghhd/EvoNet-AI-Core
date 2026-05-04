import json
import os
import requests
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "latest_threats.json"


def fetch_latest_cves():
    print("Fetching latest CVEs from CIRCL API...")
    try:
        response = requests.get("https://cve.circl.lu/api/last", timeout=15)
        return response.json()
    except Exception as e:
        print(f"Fetch error: {e}")
        return []


def update_cve_database():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_cves = {}
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                existing_cves = json.load(f)
            except json.JSONDecodeError:
                existing_cves = {}

    new_data = fetch_latest_cves()
    added_count = 0

    for item in new_data:
        cve_id = item.get("id")
        cvss_score = item.get("cvss")

        if cve_id in existing_cves:
            if existing_cves[cve_id].get("cvss_score") == "unscored" and cvss_score is not None:
                official_score = float(cvss_score)
                if official_score < 7.0:
                    del existing_cves[cve_id]
                else:
                    existing_cves[cve_id]["cvss_score"] = official_score
            continue

        is_high_risk = cvss_score is not None and float(cvss_score) >= 7.0
        is_unscored_new = cvss_score is None

        if is_high_risk or is_unscored_new:
            score = float(cvss_score) if cvss_score else "unscored"
            existing_cves[cve_id] = {
                "summary": item.get("summary", "No description"),
                "cvss_score": score,
                "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stage": "1_CVE_Harvested"
            }
            added_count += 1

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_cves, f, indent=4, ensure_ascii=False)

    print(f"Added {added_count} new CVEs. Total: {len(existing_cves)}")


if __name__ == "__main__":
    update_cve_database()
