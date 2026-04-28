import os
import json
import requests
from datetime import datetime
from federated_learning.fl_client import FLClient

# Global FL client instance
fl_client = None

def get_fl_client():
    """Get or create FL client instance"""
    global fl_client
    if fl_client is None:
        client_id = os.getenv("FL_CLIENT_ID", "default_client")
        fl_client = FLClient(client_id)
    return fl_client

def collect_user_feedback(prompt, response, feedback):
    """
    Collect user feedback for FL training
    
    :param prompt: User prompt
    :param response: AI response
    :param feedback: User feedback (positive/negative)
    """
    try:
        # Only collect positive feedback for training
        if feedback.lower() in ['positive', 'good', 'excellent', '👍', 'like']:
            feedback_score = 1.0
        elif feedback.lower() in ['negative', 'bad', 'poor', '👎', 'dislike']:
            feedback_score = 0.3  # Still collect for analysis, but low score
        else:
            feedback_score = 0.5  # Neutral
        
        client = get_fl_client()
        client.collect_training_example(prompt, response, feedback_score)
        
        print(f"📊 Đã thu thập phản hồi người dùng (score: {feedback_score})")
    except Exception as e:
        print(f"⚠️ Lỗi khi thu thập phản hồi: {e}")

def periodic_fl_training():
    """Periodically train the local model and send updates to coordinator"""
    try:
        client = get_fl_client()
        
        # Only train if we have enough data
        if len(client.local_dataset) >= 5:
            print("🏋️ Bắt đầu chu trình huấn luyện FL định kỳ")
            
            # Train locally
            local_state = client.local_train(epochs=2)
            
            if local_state:
                # In a real implementation, we would send this to a coordinator
                # For now, we'll just save it locally
                client.save_model()
                print("✅ Đã hoàn tất huấn luyện FL định kỳ")
                
                # Clear dataset to avoid overfitting
                client.local_dataset = []
            else:
                print("⚠️ Không có cập nhật để huấn luyện")
        else:
            print(f"⏭️ Chưa đủ dữ liệu để huấn luyện (cần 5, có {len(client.local_dataset)})")
            
    except Exception as e:
        print(f"⚠️ Lỗi trong chu trình huấn luyện FL: {e}")

# Example integration with Telegram feedback
def handle_telegram_feedback(message_text, ai_response):
    """Handle feedback from Telegram messages"""
    # Simple keyword-based feedback detection
    positive_keywords = ['tốt', 'hay', 'giỏi', 'chuẩn', 'đúng', 'chính xác', '👍', 'like']
    negative_keywords = ['tệ', 'dở', 'sai', 'không đúng', '👎', 'dislike']
    
    # Convert to lowercase for comparison
    text_lower = message_text.lower()
    
    # Check for explicit feedback
    if any(keyword in text_lower for keyword in positive_keywords):
        collect_user_feedback(message_text, ai_response, 'positive')
    elif any(keyword in text_lower for keyword in negative_keywords):
        collect_user_feedback(message_text, ai_response, 'negative')
    else:
        # For neutral responses, we might still collect with low confidence
        # This helps the model learn from diverse interactions
        collect_user_feedback(message_text, ai_response, 'neutral')

# Example usage in main.py
if __name__ == "__main__":
    # This would be called from main.py's telegram_worker when processing messages
    # handle_telegram_feedback("Câu trả lời rất tốt!", "Cảm ơn bạn đã phản hồi tích cực!")
    
    # Periodically called (e.g., every hour or when enough data is collected)
    # periodic_fl_training()
    pass