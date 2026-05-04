import json
import os
import requests
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "latest_threats.json"


def hunt_poc():
    if not DATA_FILE.exists():
        print("No CVE data found")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cves = json.load(f)

    github_token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    updated = False
    for cve_id, details in cves.items():
        if details.get("stage") == "1_CVE_Harvested":
            print(f"Searching PoC for {cve_id}...")

            url = f"https://api.github.com/search/repositories?q={cve_id}+poc&sort=stars&order=desc"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    items = res.json().get("items", [])
                    if items:
                        details["poc_url"] = items[0].get("html_url")
                        details["stage"] = "2_PoC_Found"
                        print(f"Found PoC: {details['poc_url']}")
                    else:
                        details["stage"] = "2_No_PoC"
                        print(f"No PoC found for {cve_id}")
                    updated = True
                elif res.status_code == 403:
                    print("GitHub rate limited, stopping")
                    break
            except Exception as e:
                print(f"Error: {e}")

            time.sleep(3)

    if updated:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cves, f, indent=4, ensure_ascii=False)
        print("PoC data saved")


if __name__ == "__main__":
    hunt_poc()
