import os
import requests
import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import hashlib
import json
import re

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


def get_embedding(text: str):
    cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env_safe("CLOUDFLARE_API_KEY")
    if not cf_id or not cf_key:
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data.get("success"):
            return data["result"]["data"][0]
        return None
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def collect_exploit_db():
    try:
        print("Collecting from Exploit-DB...")
        feed = feedparser.parse("https://www.exploit-db.com/rss.xml")
        exploits = []
        seven_days_ago = datetime.now() - timedelta(days=7)
        for entry in feed.entries:
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except Exception:
                continue
            if pub_date < seven_days_ago:
                continue
            cve_matches = re.findall(r'CVE-\d{4}-\d{4,7}', entry.title + ' ' + entry.description, re.IGNORECASE)
            exploits.append({
                'title': entry.title,
                'description': entry.description,
                'link': entry.link,
                'source': 'Exploit-DB',
                'date': entry.published,
                'cve_ids': list(set(cve_matches))
            })
        print(f"Collected {len(exploits)} exploits from Exploit-DB")
        return exploits
    except Exception as e:
        print(f"Exploit-DB error: {e}")
        return []


def collect_alienvault_otx():
    otx_key = get_env_safe("OTX_API_KEY")
    if not otx_key:
        print("OTX_API_KEY not set, skipping")
        return []
    try:
        print("Collecting from AlienVault OTX...")
        headers = {"X-OTX-API-KEY": otx_key}
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        url = f"https://otx.alienvault.com/api/v1/pulses/since/{seven_days_ago}"
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code != 200:
            return []
        pulses = res.json().get('results', [])
        otx_data = []
        for pulse in pulses:
            otx_data.append({
                'title': pulse.get('name'),
                'description': pulse.get('description'),
                'link': f"https://otx.alienvault.com/pulse/{pulse.get('id')}",
                'source': 'AlienVault OTX',
                'date': pulse.get('modified'),
                'tags': pulse.get('tags', []),
                'cve_ids': []
            })
        print(f"Collected {len(otx_data)} pulses from AlienVault OTX")
        return otx_data
    except Exception as e:
        print(f"OTX error: {e}")
        return []


def collect_packetstorm_rss():
    try:
        print("Collecting from PacketStorm...")
        feed = feedparser.parse("https://packetstormsecurity.com/headlines.rdf")
        items = []
        seven_days_ago = datetime.now() - timedelta(days=7)
        for entry in feed.entries:
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except Exception:
                continue
            if pub_date < seven_days_ago:
                continue
            cve_matches = re.findall(r'CVE-\d{4}-\d{4,7}', entry.title + ' ' + entry.description, re.IGNORECASE)
            items.append({
                'title': entry.title,
                'description': entry.description,
                'link': entry.link,
                'source': 'PacketStorm',
                'date': entry.published,
                'cve_ids': list(set(cve_matches))
            })
        print(f"Collected {len(items)} items from PacketStorm")
        return items
    except Exception as e:
        print(f"PacketStorm error: {e}")
        return []


def collect_virustotal_intel():
    vt_key = get_env_safe("VT_API_KEY")
    if not vt_key:
        print("VT_API_KEY not set, skipping")
        return []
    try:
        print("Collecting from VirusTotal...")
        headers = {"x-apikey": vt_key}
        url = "https://www.virustotal.com/api/v3/intelligence/search"
        params = {"query": "entity_type:url OR entity_type:file", "order": "last_submission_date-", "limit": 10}
        res = requests.get(url, headers=headers, params=params, timeout=30)
        if res.status_code != 200:
            return []
        items = res.json().get('data', [])
        vt_data = []
        for item in items:
            attrs = item.get('attributes', {})
            vt_data.append({
                'title': attrs.get('meaningful_name', 'Unknown'),
                'description': str(attrs.get('last_analysis_stats', {})),
                'link': f"https://www.virustotal.com/gui/file/{item.get('id')}",
                'source': 'VirusTotal',
                'date': datetime.fromtimestamp(attrs.get('first_submission_date', 0)).strftime('%Y-%m-%d'),
                'tags': attrs.get('tags', []),
                'cve_ids': []
            })
        print(f"Collected {len(vt_data)} items from VirusTotal")
        return vt_data
    except Exception as e:
        print(f"VirusTotal error: {e}")
        return []


def store_in_pinecone(intel_items, namespace="threat_intel_raw"):
    if not intel_items:
        return 0

    pc_key = get_env_safe("PINECONE_API_KEY")
    if not pc_key:
        print("PINECONE_API_KEY not set")
        return 0

    from pinecone.pinecone import Pinecone
    pc = Pinecone(api_key=pc_key)
    index = pc.Index("evonet-memory")

    vectors_to_upsert = []
    for item in intel_items:
        unique_string = item.get('link', '') or item.get('title', '') or json.dumps(item)
        item_id = hashlib.md5(unique_string.encode()).hexdigest()

        text_to_embed = f"Title: {item.get('title', '')}\nDescription: {item.get('description', '')}\nSource: {item.get('source', '')}\nDate: {item.get('date', '')}"
        embedding = get_embedding(text_to_embed)
        if embedding is None:
            continue

        metadata = {
            'source': item.get('source', ''),
            'title': item.get('title', '')[:200],
            'date': item.get('date', ''),
            'link': item.get('link', '')[:500],
            'text': text_to_embed[:1000]
        }
        for key in ['cve_ids', 'tags']:
            if key in item and item[key]:
                metadata[key] = str(item[key])[:500]

        vectors_to_upsert.append({'id': item_id, 'values': embedding, 'metadata': metadata})

    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i+batch_size]
        index.upsert(vectors=batch, namespace=namespace)

    print(f"Stored {len(vectors_to_upsert)} items in Pinecone")
    return len(vectors_to_upsert)


def main():
    print("Starting threat intelligence collection...")
    send_telegram("🤖 <b>THREAT INTEL:</b>\nCollecting from multiple sources...")

    all_intel = []
    all_intel.extend(collect_exploit_db())
    all_intel.extend(collect_alienvault_otx())
    all_intel.extend(collect_packetstorm_rss())
    all_intel.extend(collect_virustotal_intel())

    if not all_intel:
        print("No intelligence items collected")
        return

    print(f"Total items collected: {len(all_intel)}")
    stored = store_in_pinecone(all_intel)

    if stored > 0:
        send_telegram(f"✅ <b>THREAT INTEL COMPLETE:</b>\nCollected and stored {stored} threat intelligence items")
    else:
        send_telegram("⚠️ Collection succeeded but Pinecone storage failed")


if __name__ == "__main__":
    main()
