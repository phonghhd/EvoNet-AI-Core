import os
import json
from typing import Dict, List, Any
from pathlib import Path
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/phong/evonet-core/.env", override=True)

class FeedbackLearningSystem:
    """Advanced feedback learning system for continuous improvement"""
    
    def __init__(self):
        self.feedback_log_path = Path("/home/phong/evonet-core/logs/feedback_log.json")
        self.model_weights_path = Path("/home/phong/evonet-core/models/feedback_weights.json")
        self.feedback_history = []
        self.feedback_weights = {
            "positive": 1.0,
            "negative": 0.3,
            "neutral": 0.5
        }
        self._load_feedback_data()
        self._load_model_weights()
    
    def _load_feedback_data(self):
        """Load feedback history from file"""
        try:
            if self.feedback_log_path.exists():
                with open(self.feedback_log_path, "r", encoding="utf-8") as f:
                    self.feedback_history = json.load(f)
                print(f"Loaded {len(self.feedback_history)} feedback entries")
        except Exception as e:
            print(f"Error loading feedback data: {e}")
            self.feedback_history = []
    
    def _load_model_weights(self):
        """Load model weights from file"""
        try:
            if self.model_weights_path.exists():
                with open(self.model_weights_path, "r", encoding="utf-8") as f:
                    self.feedback_weights = json.load(f)
        except Exception as e:
            print(f"Error loading model weights: {e}")
    
    def _save_feedback_data(self):
        """Save feedback history to file"""
        try:
            self.feedback_log_path.parent.mkdir(exist_ok=True)
            with open(self.feedback_log_path, "w", encoding="utf-8") as f:
                json.dump(self.feedback_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving feedback data: {e}")
    
    def _save_model_weights(self):
        """Save model weights to file"""
        try:
            self.model_weights_path.parent.mkdir(exist_ok=True)
            with open(self.model_weights_path, "w", encoding="utf-8") as f:
                json.dump(self.feedback_weights, f, indent=2)
        except Exception as e:
            print(f"Error saving model weights: {e}")
    
    def collect_feedback(self, user_input: str, ai_response: str, feedback: str, context: Dict = None) -> bool:
        """Collect user feedback for learning"""
        try:
            feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "ai_response": ai_response,
                "feedback": feedback.lower(),
                "context": context or {},
                "weight": self.feedback_weights.get(feedback.lower(), 0.5)
            }
            
            self.feedback_history.append(feedback_entry)
            self._save_feedback_data()
            
            # Update model weights based on feedback patterns
            self._update_model_weights(feedback.lower())
            
            print(f"Collected {feedback} feedback")
            return True
        except Exception as e:
            print(f"Error collecting feedback: {e}")
            return False
    
    def _update_model_weights(self, feedback_type: str):
        """Update model weights based on feedback patterns"""
        try:
            # Simple moving average approach for weight adjustment
            if feedback_type == "positive":
                self.feedback_weights["positive"] = min(1.0, self.feedback_weights["positive"] + 0.01)
                self.feedback_weights["negative"] = max(0.1, self.feedback_weights["negative"] - 0.005)
            elif feedback_type == "negative":
                self.feedback_weights["negative"] = min(0.9, self.feedback_weights["negative"] + 0.02)
                self.feedback_weights["positive"] = max(0.5, self.feedback_weights["positive"] - 0.01)
            
            self._save_model_weights()
        except Exception as e:
            print(f"Error updating model weights: {e}")
    
    def analyze_feedback_patterns(self) -> Dict[str, Any]:
        """Analyze feedback patterns for insights"""
        try:
            if not self.feedback_history:
                return {"message": "No feedback data available"}
            
            # Calculate statistics
            total_feedback = len(self.feedback_history)
            positive_count = sum(1 for f in self.feedback_history if f["feedback"] == "positive")
            negative_count = sum(1 for f in self.feedback_history if f["feedback"] == "negative")
            neutral_count = sum(1 for f in self.feedback_history if f["feedback"] == "neutral")
            
            # Calculate recent trends (last 50 entries)
            recent_feedback = self.feedback_history[-50:] if len(self.feedback_history) > 50 else self.feedback_history
            recent_positive = sum(1 for f in recent_feedback if f["feedback"] == "positive")
            recent_negative = sum(1 for f in recent_feedback if f["feedback"] == "negative")
            
            # Analyze context patterns
            context_patterns = {}
            for feedback in self.feedback_history:
                context = feedback.get("context", {})
                for key, value in context.items():
                    if key not in context_patterns:
                        context_patterns[key] = {}
                    if value not in context_patterns[key]:
                        context_patterns[key][value] = {"positive": 0, "negative": 0, "neutral": 0}
                    context_patterns[key][value][feedback["feedback"]] += 1
            
            return {
                "total_feedback": total_feedback,
                "positive_percentage": (positive_count / total_feedback) * 100 if total_feedback > 0 else 0,
                "negative_percentage": (negative_count / total_feedback) * 100 if total_feedback > 0 else 0,
                "neutral_percentage": (neutral_count / total_feedback) * 100 if total_feedback > 0 else 0,
                "recent_positive_trend": (recent_positive / len(recent_feedback)) * 100 if recent_feedback else 0,
                "recent_negative_trend": (recent_negative / len(recent_feedback)) * 100 if recent_feedback else 0,
                "context_patterns": context_patterns,
                "model_weights": self.feedback_weights
            }
        except Exception as e:
            print(f"Error analyzing feedback patterns: {e}")
            return {"error": str(e)}
    
    def get_feedback_weighted_response(self, prompt: str) -> float:
        """Get weighted feedback score for a given prompt"""
        try:
            # In a real implementation, this would use ML models
            # For now, we'll use a simple keyword-based approach
            positive_keywords = ["tốt", "hay", "giỏi", "chuẩn", "đúng", "chính xác", "👍", "like"]
            negative_keywords = ["tệ", "dở", "sai", "không đúng", "👎", "dislike"]
            
            positive_score = sum(1 for keyword in positive_keywords if keyword in prompt.lower())
            negative_score = sum(1 for keyword in negative_keywords if keyword in prompt.lower())
            
            # Calculate weighted score
            if positive_score > 0 and negative_score == 0:
                return self.feedback_weights["positive"]
            elif negative_score > 0 and positive_score == 0:
                return self.feedback_weights["negative"]
            else:
                return self.feedback_weights["neutral"]
        except Exception as e:
            print(f"Error calculating feedback weight: {e}")
            return 0.5
    
    def generate_feedback_report(self) -> str:
        """Generate a feedback analysis report"""
        try:
            analysis = self.analyze_feedback_patterns()
            
            if "error" in analysis:
                return f"❌ Error in analysis: {analysis['error']}"
            
            report = "📊 <b>BÁO CÁO PHẢN HỒI NGƯỜI DÙNG:</b>\n"
            report += f"Tổng số phản hồi: {analysis['total_feedback']}\n"
            report += f"Phản hồi tích cực: {analysis['positive_percentage']:.1f}%\n"
            report += f"Phản hồi tiêu cực: {analysis['negative_percentage']:.1f}%\n"
            report += f"Xu hướng gần đây (tích cực): {analysis['recent_positive_trend']:.1f}%\n"
            report += f"Xu hướng gần đây (tiêu cực): {analysis['recent_negative_trend']:.1f}%\n\n"
            
            # Add context pattern insights
            if analysis["context_patterns"]:
                report += "Phân tích theo ngữ cảnh:\n"
                for context_key, context_values in list(analysis["context_patterns"].items())[:3]:
                    report += f"- {context_key}: {len(context_values)} giá trị khác nhau\n"
            
            return report
        except Exception as e:
            return f"❌ Error generating feedback report: {e}"

class AdvancedFeedbackLearning(FeedbackLearningSystem):
    """Advanced feedback learning with machine learning capabilities"""
    
    def __init__(self):
        super().__init__()
        self.feedback_model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize machine learning model for feedback analysis"""
        try:
            # This would typically load a pre-trained model
            # For now, we'll use a simple approach
            print("Initialized feedback learning model")
        except Exception as e:
            print(f"Error initializing model: {e}")
    
    def predict_response_quality(self, user_input: str, ai_response: str) -> float:
        """Predict the quality of AI response based on feedback patterns"""
        try:
            # Simple keyword-based prediction for demonstration
            # In a real implementation, this would use a trained ML model
            feedback_weight = self.get_feedback_weighted_response(user_input)
            return feedback_weight
        except Exception as e:
            print(f"Error predicting response quality: {e}")
            return 0.5
    
    def adapt_response_strategy(self, user_input: str, ai_response: str, feedback: str) -> Dict[str, Any]:
        """Adapt response strategy based on feedback"""
        try:
            adaptation = {
                "confidence_adjustment": 0.0,
                "style_changes": [],
                "content_focus": []
            }
            
            # Adjust confidence based on feedback
            if feedback.lower() == "positive":
                adaptation["confidence_adjustment"] = 0.1  # Increase confidence
                adaptation["style_changes"].append("maintain_current_approach")
            elif feedback.lower() == "negative":
                adaptation["confidence_adjustment"] = -0.2  # Decrease confidence
                adaptation["style_changes"].append("be_more_detailed")
                adaptation["style_changes"].append("provide_examples")
            
            # Analyze content focus based on user input
            if "code" in user_input.lower() or "lập trình" in user_input.lower():
                adaptation["content_focus"].append("technical_detail")
            if "giải thích" in user_input.lower() or "explain" in user_input.lower():
                adaptation["content_focus"].append("explanatory")
            
            return adaptation
        except Exception as e:
            print(f"Error adapting response strategy: {e}")
            return {"error": str(e)}

def main():
    """Example usage of feedback learning system"""
    print("Initializing feedback learning system...")
    
    # Create feedback learning system
    feedback_system = AdvancedFeedbackLearning()
    
    # Example feedback collection
    feedback_system.collect_feedback(
        user_input="Viết code Python để kiểm tra số nguyên tố",
        ai_response="def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
        feedback="positive",
        context={"language": "python", "topic": "math"}
    )
    
    feedback_system.collect_feedback(
        user_input="Cách phòng chống SQL injection?",
        ai_response="Để phòng chống SQL injection, bạn nên sử dụng prepared statements và parameterized queries.",
        feedback="negative",
        context={"topic": "security", "detail_level": "basic"}
    )
    
    # Generate feedback report
    report = feedback_system.generate_feedback_report()
    print(report)
    
    # Analyze feedback patterns
    patterns = feedback_system.analyze_feedback_patterns()
    print("Feedback patterns analysis:", patterns)

if __name__ == "__main__":
    main()