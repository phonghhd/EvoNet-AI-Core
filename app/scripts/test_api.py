import os
import requests
from dotenv import load_dotenv

# 1. Ép hệ thống đọc file .env (Sếp nhớ đảm bảo file .env đang nằm đúng chỗ này)
load_dotenv("/app/.env", override=True)

def mask_key(key):
    if not key: return "❌ TRỐNG LỐC (Chưa đọc được file .env)"
    if len(key) < 10: return f"❌ KEY QUÁ NGẮN (Lỗi copy/paste?): {key}"
    return f"✅ {key[:5]}...{key[-5:]} (Tổng dài {len(key)} ký tự)"

print("\n" + "="*50)
print("🔍 MÁY NỘI SOI TÌM LỖI API CHUYÊN SÂU")
print("="*50)

# Lấy chìa khóa từ hệ thống
groq_key = os.getenv("GROQ_API_KEY")
cf_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
cf_key = os.getenv("CLOUDFLARE_API_KEY")

print("\n[BƯỚC 1: KIỂM TRA TÌNH TRẠNG CHÌA KHÓA]")
print(f"🔑 GROQ_KEY:   {mask_key(groq_key)}")
print(f"🔑 CF_ID:      {mask_key(cf_id)}")
print(f"🔑 CF_KEY:     {mask_key(cf_key)}")

print("\n[BƯỚC 2: BẮN TÍN HIỆU LÊN MÁY CHỦ GROQ]")
if groq_key:
    try:
        res_groq = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "Ping"}]},
            timeout=15
        )
        print(f"➜ Mã phản hồi: {res_groq.status_code}")
        if res_groq.status_code == 200:
            print("✅ GROQ PHẢN HỒI: " + res_groq.json()["choices"][0]["message"]["content"])
        else:
            print(f"❌ GROQ BÁO LỖI: {res_groq.text}") # In thẳng câu chửi của Groq ra màn hình
    except Exception as e:
        print(f"⚠️ Lỗi kết nối mạng: {e}")

print("\n[BƯỚC 3: BẮN TÍN HIỆU LÊN MÁY CHỦ CLOUDFLARE]")
if cf_id and cf_key:
    try:
        url_cf = f"https://api.cloudflare.com/client/v4/accounts/{cf_id}/ai/run/@cf/qwen/qwen2.5-coder-32b-instruct"
        res_cf = requests.post(
            url_cf,
            headers={"Authorization": f"Bearer {cf_key}"},
            json={"messages": [{"role": "user", "content": "Ping"}]},
            timeout=15
        )
        print(f"➜ Mã phản hồi: {res_cf.status_code}")
        if res_cf.status_code == 200:
            print("✅ CF PHẢN HỒI: " + res_cf.json().get("result", {}).get("response", "Không có nội dung"))
        else:
            print(f"❌ CF BÁO LỖI: {res_cf.text}") # In thẳng câu chửi của CF ra màn hình
    except Exception as e:
        print(f"⚠️ Lỗi kết nối mạng: {e}")

print("\n" + "="*50)
