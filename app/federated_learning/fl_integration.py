import os
import sys
import json
import requests
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from federated_learning.fl_client import FLClient

fl_client = None


def get_fl_client():
    global fl_client
    if fl_client is None:
        client_id = os.getenv("FL_CLIENT_ID", "default_client")
        fl_client = FLClient(client_id)
    return fl_client


def collect_user_feedback(prompt, response, feedback):
    try:
        score_map = {
            'positive': 1.0, 'good': 1.0, 'excellent': 1.0,
            'negative': 0.3, 'bad': 0.3, 'poor': 0.3,
        }
        score = score_map.get(feedback.lower(), 0.5)
        get_fl_client().collect_training_example(prompt, response, score)
    except Exception as e:
        print(f"Feedback collection error: {e}")


def periodic_fl_training():
    try:
        client = get_fl_client()
        if len(client.local_dataset) >= 5:
            print(f"Starting FL training with {len(client.local_dataset)} examples")
            state = client.local_train(epochs=2)
            if state:
                client.save_model()
                client.local_dataset = []
                print("FL training complete")
        else:
            print(f"Not enough data for FL ({len(client.local_dataset)}/5)")
    except Exception as e:
        print(f"FL training error: {e}")


def handle_telegram_feedback(message_text, ai_response):
    positive = ['tốt', 'hay', 'giỏi', 'chuẩn', 'đúng', '👍']
    negative = ['tệ', 'dở', 'sai', 'không đúng', '👎']
    text_lower = message_text.lower()
    if any(kw in text_lower for kw in positive):
        collect_user_feedback(message_text, ai_response, 'positive')
    elif any(kw in text_lower for kw in negative):
        collect_user_feedback(message_text, ai_response, 'negative')
