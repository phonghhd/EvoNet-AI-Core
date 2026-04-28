import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
import subprocess
from system_watchdog import regex_blacklist_guardrail

# Load environment variables
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
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try: 
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

class MultiModalAI:
    """Multi-modal AI system for analyzing security videos and lectures"""
    
    def __init__(self):
        self.openai_api_key = get_env_safe("OPENAI_API_KEY")
        self.cloudflare_account_id = get_env_safe("CLOUDFLARE_ACCOUNT_ID")
        self.cloudflare_api_key = get_env_safe("CLOUDFLARE_API_KEY")
        
    def extract_audio_from_video(self, video_path: str) -> str:
        """Extract audio from video file"""
        try:
            # Use ffmpeg to extract audio
            audio_path = video_path.replace(".mp4", ".wav").replace(".avi", ".wav").replace(".mkv", ".wav")
            
            # Check if ffmpeg is available
            result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
            if result.returncode != 0:
                print("ffmpeg not installed, installing...")
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "ffmpeg"], check=True)
            
            # Extract audio
            subprocess.run([
                "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", 
                "-ar", "44100", "-ac", "2", audio_path
            ], check=True)
            
            return audio_path
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return None
    
    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio to text using OpenAI Whisper"""
        try:
            if not self.openai_api_key:
                print("OpenAI API key not configured")
                return None
            
            # Use OpenAI Whisper API for transcription
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            with open(audio_path, "rb") as audio_file:
                files = {"file": audio_file}
                data = {"model": "whisper-1"}
                
                response = requests.post(url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    return response.json()["text"]
                else:
                    print(f"Error transcribing audio: {response.text}")
                    return None
        except Exception as e:
            print(f"Error in transcription: {e}")
            return None
    
    def analyze_transcript(self, transcript: str) -> Dict:
        """Analyze transcript for security insights using Cloudflare AI"""
        try:
            if not self.cloudflare_account_id or not self.cloudflare_api_key:
                print("Cloudflare credentials not configured")
                return None
            
            # Use Cloudflare AI to analyze the transcript
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.cloudflare_account_id}/ai/run/@cf/meta/llama-2-7b-chat-fp16"
            headers = {
                "Authorization": f"Bearer {self.cloudflare_api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Phân tích nội dung sau để tìm hiểu các vấn đề bảo mật:
            
            {transcript}
            
            Hãy xác định:
            1. Các lỗ hổng bảo mật được đề cập
            2. Các kỹ thuật tấn công được mô tả
            3. Các biện pháp phòng thủ được khuyến nghị
            4. Các khái niệm bảo mật quan trọng
            
            Trả lời bằng tiếng Việt chuyên nghiệp.
            """
            
            payload = {
                "messages": [
                    {"role": "system", "content": "Bạn là chuyên gia bảo mật AI."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()["result"]["response"]
            else:
                print(f"Error analyzing transcript: {response.text}")
                return None
        except Exception as e:
            print(f"Error analyzing transcript: {e}")
            return None
    
    def process_video(self, video_path: str) -> Dict:
        """Process a security video and extract insights"""
        try:
            # Extract audio from video
            send_telegram("🔊 <b>XỬ LÝ VIDEO:</b> Đang trích xuất âm thanh...")
            audio_path = self.extract_audio_from_video(video_path)
            if not audio_path:
                return {"success": False, "error": "Failed to extract audio"}
            
            # Transcribe audio to text
            send_telegram("📝 <b>XỬ LÝ VIDEO:</b> Đang chuyển đổi giọng nói thành văn bản...")
            transcript = self.transcribe_audio(audio_path)
            if not transcript:
                return {"success": False, "error": "Failed to transcribe audio"}
            
            # Analyze transcript for security insights
            send_telegram("🧠 <b>XỬ LÝ VIDEO:</b> Đang phân tích nội dung bảo mật...")
            analysis = self.analyze_transcript(transcript)
            if not analysis:
                return {"success": False, "error": "Failed to analyze transcript"}
            
            # Clean up temporary audio file
            try:
                # Kiểm tra an toàn trước khi xóa file
                regex_blacklist_guardrail(audio_path)
                os.remove(audio_path)
            except:
                pass
            
            return {
                "success": True,
                "transcript": transcript,
                "analysis": analysis
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_security_lecture(self, video_url: str) -> Dict:
        """Process a security lecture video from URL"""
        try:
            # Download video if it's a URL
            if video_url.startswith("http"):
                send_telegram("📥 <b>TẢI VIDEO:</b> Đang tải video từ URL...")
                video_path = "/tmp/temp_video.mp4"
                
                # Download video
                response = requests.get(video_url)
                if response.status_code == 200:
                    with open(video_path, "wb") as f:
                        f.write(response.content)
                else:
                    return {"success": False, "error": "Failed to download video"}
            else:
                video_path = video_url  # Assume it's a local file path
            
            # Process the video
            result = self.process_video(video_path)
            
            # Clean up temporary video file if downloaded
            if video_url.startswith("http"):
                try:
                    # Kiểm tra an toàn trước khi xóa file
                    regex_blacklist_guardrail(video_path)
                    os.remove(video_path)
                except:
                    pass
            
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_insights_report(self, analysis_result: Dict) -> str:
        """Generate a report of security insights from video analysis"""
        if not analysis_result.get("success", False):
            return f"❌ <b>PHÂN TÍCH VIDEO THẤT BẠI:</b>\n{analysis_result.get('error', 'Unknown error')}"
        
        analysis = analysis_result.get("analysis", "")
        if not analysis:
            return "⚠️ <b>PHÂN TÍCH VIDEO:</b>\nKhông tìm thấy thông tin bảo mật trong video."
        
        # Create a summary report
        report = "🔍 <b>PHÂN TÍCH VIDEO BẢO MẬT:</b>\n"
        report += "Đã phân tích video và tìm thấy các thông tin sau:\n\n"
        report += analysis[:800]  # Limit length for Telegram
        
        if len(analysis) > 800:
            report += "\n\n... (xem thêm trong logs)"
        
        return report

def main():
    """Main function to process security videos"""
    print("Starting multi-modal AI processing...")
    send_telegram("🎥 <b>AI ĐA PHƯƠNG TIỆN:</b>\nĐang xử lý video/bài giảng bảo mật...")
    
    # Example usage - in practice, you would get video URLs from a queue or user input
    ai = MultiModalAI()
    
    # Example: Process a security lecture (replace with actual URL or file path)
    # video_url = "https://example.com/security-lecture.mp4"
    # result = ai.process_security_lecture(video_url)
    # report = ai.generate_insights_report(result)
    # send_telegram(report)
    
    send_telegram("✅ <b>HOÀN TẤT XỬ LÝ:</b>\nHệ thống AI đa phương tiện đã sẵn sàng.")

if __name__ == "__main__":
    main()