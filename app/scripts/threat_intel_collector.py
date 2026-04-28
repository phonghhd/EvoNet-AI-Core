import os
import requests
import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
import hashlib
import json

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

def get_pinecone_index():
    pc_key = get_env_safe("PINECONE_API_KEY")
    if not pc_key:
        raise Exception("PINECONE_API_KEY not set")
    from pinecone.pinecone import Pinecone
    pc = Pinecone(api_key=pc_key)
    return pc.Index("evonet-memory")

def get_embedding(text: str):
    """Use Cloudflare to get embedding"""
    cf_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
    cf_key = get_env_safe("CLOUDFLARE_API_KEY")
    if not cf_id or not cf_key:
        raise Exception("Cloudflare credentials not set")
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/baai/bge-base-en-v1.5"
    headers = {"Authorization": f"Bearer {cf_key}"}
    try:
        res = requests.post(url, headers=headers, json={"text": [text]}, timeout=15)
        data = res.json()
        if data.get("success"):
            return data["result"]["data"][0]
        else:
            print(f"Cloudflare embedding error: {data.get('errors')}")
            return None
    except Exception as e:
        print(f"Error calling Cloudflare embedding API: {e}")
        return None

def collect_exploit_db():
    """Collect latest exploits from Exploit-DB RSS feed"""
    try:
        print("Collecting from Exploit-DB...")
        url = "https://www.exploit-db.com/rss.xml"
        feed = feedparser.parse(url)
        exploits = []
        seven_days_ago = datetime.now() - timedelta(days=7)
        for entry in feed.entries:
            # Parse the published date
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except:
                # If parsing fails, skip
                continue
            
            if pub_date < seven_days_ago:
                continue
                
            # Extract CVE IDs from title or description if present
            import re
            cve_matches = re.findall(r'CVE-\d{4}-\d{4,7}', entry.title + ' ' + entry.description, re.IGNORECASE)
            
            exploit_data = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.link,
                'source': 'Exploit-DB',
                'date': entry.published,
                'cve_ids': list(set(cve_matches))  # Remove duplicates
            }
            exploits.append(exploit_data)
        
        print(f"Collected {len(exploits)} exploits from Exploit-DB")
        return exploits
    except Exception as e:
        print(f"Error collecting from Exploit-DB: {e}")
        send_telegram(f"⚠️ Lỗi khi thu thập từ Exploit-DB: {e}")
        return []

def collect_alienvault_otx():
    """Collect pulses from AlienVault OTX (requires API key)"""
    otx_key = get_env_safe("OTX_API_KEY")
    if not otx_key:
        print("OTX API key not set, skipping AlienVault OTX collection")
        return []
    
    try:
        print("Collecting from AlienVault OTX...")
        headers = {"X-OTX-API-KEY": otx_key}
        url = "https://otx.alienvault.com/api/v1/pulses/since/"
        # Get pulses from the last 7 days
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        url += seven_days_ago
        
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code != 200:
            print(f"OTX API error: {res.status_code} - {res.text}")
            return []
        
        data = res.json()
        pulses = data.get('results', [])
        
        otx_data = []
        for pulse in pulses:
            # Extract relevant information
            otx_data.append({
                'title': pulse.get('name'),
                'description': pulse.get('description'),
                'link': f"https://otx.alienvault.com/pulse/{pulse.get('id')}",
                'source': 'AlienVault OTX',
                'date': pulse.get('modified'),
                'tags': pulse.get('tags', []),
                'malware_families': pulse.get('malware_families', []),
                'attack_ids': pulse.get('attack_ids', [])
            })
        
        print(f"Collected {len(otx_data)} pulses from AlienVault OTX")
        return otx_data
    except Exception as e:
        print(f"Error collecting from AlienVault OTX: {e}")
        send_telegram(f"⚠️ Lỗi khi thu thập từ AlienVault OTX: {e}")
        return []


def collect_packetstorm_rss():
    """Collect latest security reports from PacketStorm RSS feed"""
    try:
        print("Collecting from PacketStorm...")
        url = "https://packetstormsecurity.com/headlines.rdf"
        feed = feedparser.parse(url)
        items = []
        seven_days_ago = datetime.now() - timedelta(days=7)
        for entry in feed.entries:
            # Parse the published date
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except:
                # If parsing fails, skip
                continue
            
            if pub_date < seven_days_ago:
                continue
                
            # Extract CVE IDs from title or description if present
            import re
            cve_matches = re.findall(r'CVE-\d{4}-\d{4,7}', entry.title + ' ' + entry.description, re.IGNORECASE)
            
            item_data = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.link,
                'source': 'PacketStorm',
                'date': entry.published,
                'cve_ids': list(set(cve_matches))  # Remove duplicates
            }
            items.append(item_data)
        
        print(f"Collected {len(items)} items from PacketStorm")
        return items
    except Exception as e:
        print(f"Error collecting from PacketStorm: {e}")
        send_telegram(f"⚠️ Lỗi khi thu thập từ PacketStorm: {e}")
        return []


def collect_virustotal_intel():
    """Collect threat intelligence from VirusTotal (requires API key)"""
    vt_key = get_env_safe("VT_API_KEY")
    if not vt_key:
        print("VirusTotal API key not set, skipping VirusTotal collection")
        return []
    
    try:
        print("Collecting from VirusTotal...")
        headers = {"x-apikey": vt_key}
        # Get recent intelligence reports
        url = "https://www.virustotal.com/api/v3/intelligence/search"
        params = {
            "query": "entity_type:url OR entity_type:file",
            "order": "last_submission_date-",
            "limit": 10
        }
        
        res = requests.get(url, headers=headers, params=params, timeout=30)
        if res.status_code != 200:
            print(f"VirusTotal API error: {res.status_code} - {res.text}")
            return []
        
        data = res.json()
        items = data.get('data', [])
        
        vt_data = []
        for item in items:
            attributes = item.get('attributes', {})
            vt_data.append({
                'title': attributes.get('meaningful_name', 'Unknown'),
                'description': attributes.get('last_analysis_stats', {}),
                'link': f"https://www.virustotal.com/gui/file/{item.get('id')}",
                'source': 'VirusTotal',
                'date': datetime.fromtimestamp(attributes.get('first_submission_date', 0)).strftime('%Y-%m-%d'),
                'tags': attributes.get('tags', []),
                'threat_classification': attributes.get('popular_threat_classification', {})
            })
        
        print(f"Collected {len(vt_data)} items from VirusTotal")
        return vt_data
    except Exception as e:
        print(f"Error collecting from VirusTotal: {e}")
        send_telegram(f"⚠️ Lỗi khi thu thập từ VirusTotal: {e}")
        return []

def store_in_pinecone(intel_items, namespace="threat_intel_raw"):
    """Store intelligence items in Pinecone"""
    if not intel_items:
        print("No intelligence items to store")
        return 0
    
    # Load environment variables
    load_dotenv("/home/phong/evonet-core/.env", override=True)
    
    try:
        pc_key = os.getenv("PINECONE_API_KEY")
        if not pc_key:
            print("PINECONE_API_KEY not set, skipping Pinecone storage")
            return 0
            
        from pinecone.pinecone import Pinecone
        pc = Pinecone(api_key=pc_key)
        index = pc.Index("evonet-memory")
        
        vectors_to_upsert = []
        
        for item in intel_items:
            # Create a unique ID based on source and link or title
            unique_string = item.get('link', '') or item.get('title', '') or json.dumps(item)
            item_id = hashlib.md5(unique_string.encode()).hexdigest()
            
            # Prepare text for embedding
            text_to_embed = f"""
            Title: {item.get('title', '')}
            Description: {item.get('description', '')}
            Source: {item.get('source', '')}
            Date: {item.get('date', '')}
            """.strip()
            
            # Get embedding
            embedding = get_embedding(text_to_embed)
            if embedding is None:
                print(f"Failed to get embedding for item: {item.get('title', 'Unknown')}")
                continue
            
            # Prepare metadata
            metadata = {
                'source': item.get('source', ''),
                'title': item.get('title', '')[:200],  # Limit length
                'date': item.get('date', ''),
                'link': item.get('link', '')[:500],
                'text': text_to_embed[:1000]  # Store a snippet
            }
            # Add any extra fields that are present
            for key in ['cve_ids', 'tags', 'malware_families', 'attack_ids']:
                if key in item and item[key]:
                    metadata[key] = str(item[key])[:500]  # Convert to string and limit length
            
            vectors_to_upsert.append({
                'id': item_id,
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i+batch_size]
            index.upsert(vectors=batch, namespace=namespace)
            print(f"Upserted batch {i//batch_size + 1}/{(len(vectors_to_upsert)-1)//batch_size + 1} to namespace {namespace}")
        
        print(f"Successfully stored {len(vectors_to_upsert)} intelligence items in Pinecone namespace {namespace}")
        return len(vectors_to_upsert)
    except Exception as e:
        print(f"Error storing in Pinecone: {e}")
        return 0
    
    try:
        index = get_pinecone_index()
        vectors_to_upsert = []
        
        for item in intel_items:
            # Create a unique ID based on source and link or title
            unique_string = item.get('link', '') or item.get('title', '') or json.dumps(item)
            item_id = hashlib.md5(unique_string.encode()).hexdigest()
            
            # Prepare text for embedding
            text_to_embed = f"""
            Title: {item.get('title', '')}
            Description: {item.get('description', '')}
            Source: {item.get('source', '')}
            Date: {item.get('date', '')}
            """.strip()
            
            # Get embedding
            embedding = get_embedding(text_to_embed)
            if embedding is None:
                print(f"Failed to get embedding for item: {item.get('title', 'Unknown')}")
                continue
            
            # Prepare metadata
            metadata = {
                'source': item.get('source', ''),
                'title': item.get('title', '')[:200],  # Limit length
                'date': item.get('date', ''),
                'link': item.get('link', '')[:500],
                'text': text_to_embed[:1000]  # Store a snippet
            }
            # Add any extra fields that are present
            for key in ['cve_ids', 'tags', 'malware_families', 'attack_ids']:
                if key in item and item[key]:
                    metadata[key] = str(item[key])[:500]  # Convert to string and limit length
            
            vectors_to_upsert.append({
                'id': item_id,
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i+batch_size]
            index.upsert(vectors=batch, namespace=namespace)
            print(f"Upserted batch {i//batch_size + 1}/{(len(vectors_to_upsert)-1)//batch_size + 1} to namespace {namespace}")
        
        print(f"Successfully stored {len(vectors_to_upsert)} intelligence items in Pinecone namespace {namespace}")
        return len(vectors_to_upsert)
    except Exception as e:
        print(f"Error storing in Pinecone: {e}")
        send_telegram(f"⚠️ Lỗi khi lưu trữ thông tin vào Pinecone: {e}")
        return 0

def main():
    """Main function to collect threat intelligence and store in Pinecone"""
    print("Starting threat intelligence collection...")
    send_telegram("🤖 <b>BẮT ĐẦU THU THẬP THÔNG TIN ĐỘ NGU GHI NHẬN</b>\nĐang thu thập dữ liệu từ các nguồn đe dọa...")
    
    all_intel = []
    
    # Collect from various sources
    exploit_db_items = collect_exploit_db()
    all_intel.extend(exploit_db_items)
    
    otx_items = collect_alienvault_otx()
    all_intel.extend(otx_items)
    
    # Collect from PacketStorm
    packetstorm_items = collect_packetstorm_rss()
    all_intel.extend(packetstorm_items)
    
    # Collect from VirusTotal
    vt_items = collect_virustotal_intel()
    all_intel.extend(vt_items)
    
    # TODO: Add more sources as needed (VirusTotal, etc.)
    
    if not all_intel:
        print("No intelligence items collected")
        send_telegram("⚠️ Không thu thập được thông tin đe dọa nào")
        return
    
    print(f"Total intelligence items collected: {len(all_intel)}")
    
    # Store in Pinecone
    stored_count = store_in_pinecone(all_intel, namespace="threat_intel_raw")
    
    if stored_count > 0:
        send_telegram(f"✅ <b>HOÀN TẤT THU THẬP THÔNG TIN ĐỘ NGU</b>\nĐã thu thập và lưu trữ {stored_count} mẫu thông tin đe dọa mới vào hệ thống.")
    else:
        send_telegram("⚠️ Thu thập thông tin thành công nhưng không lưu trữ được vào Pinecone")

if __name__ == "__main__":
    main()