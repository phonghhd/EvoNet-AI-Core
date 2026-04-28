import os
import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.utils.data import Dataset, DataLoader
import json
import hashlib
from datetime import datetime

class FLDataset(Dataset):
    """Dataset for Federated Learning"""
    def __init__(self, data_list, tokenizer, max_length=512):
        self.data = data_list
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        # Tokenize prompt and response
        prompt = item.get('prompt', '')
        response = item.get('response', '')
        
        # Combine prompt and response for training
        text = f"Human: {prompt}\nAssistant: {response}"
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten()
        }

class FLClient:
    """Federated Learning Client"""
    def __init__(self, client_id, model_name="qwen2.5-coder:14b", model_path=None):
        self.client_id = client_id
        self.model_name = model_name
        self.model_path = model_path or f"/app/models/fl_model_{client_id}"
        
        # Initialize model and tokenizer
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Training data storage
        self.local_dataset = []
        
        # Load existing model if available
        self._load_model()
    
    def _load_model(self):
        """Load existing model if available"""
        try:
            if os.path.exists(f"{self.model_path}.pt"):
                self.model.load_state_dict(torch.load(f"{self.model_path}.pt"))
                print(f"🔄 Đã tải mô hình FL từ {self.model_path}.pt")
        except Exception as e:
            print(f"⚠️ Không thể tải mô hình FL: {e}")
    
    def collect_training_example(self, prompt, response, feedback_score=1.0):
        """
        Collect a training example from user interaction
        
        :param prompt: User prompt
        :param response: AI response
        :param feedback_score: User feedback score (0.0-1.0)
        """
        # Only collect examples with positive feedback
        if feedback_score >= 0.7:
            example = {
                'prompt': prompt,
                'response': response,
                'feedback_score': feedback_score,
                'timestamp': datetime.now().isoformat(),
                'hash': hashlib.md5(f"{prompt}{response}".encode()).hexdigest()
            }
            self.local_dataset.append(example)
            print(f"📚 Đã thu thập ví dụ huấn luyện (score: {feedback_score})")
    
    def local_train(self, epochs=1, learning_rate=5e-5, batch_size=4):
        """
        Train model on local data
        
        :param epochs: Number of training epochs
        :param learning_rate: Learning rate
        :param batch_size: Batch size for training
        :return: Model state dict
        """
        if not self.local_dataset:
            print("⚠️ Không có dữ liệu huấn luyện cục bộ")
            return None
        
        print(f"🏋️ Bắt đầu huấn luyện FL cục bộ với {len(self.local_dataset)} ví dụ")
        
        # Create dataset and dataloader
        dataset = FLDataset(self.local_dataset, self.tokenizer)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Setup optimizer
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)
        self.model.train()
        
        # Training loop
        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                optimizer.zero_grad()
                
                # Forward pass
                outputs = self.model(
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask'],
                    labels=batch['input_ids']  # Self-supervised learning
                )
                
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(dataloader)
            print(f"📊 Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}")
        
        self.model.eval()
        print("✅ Huấn luyện FL cục bộ hoàn tất")
        
        # Return model state for aggregation
        return self.model.state_dict()
    
    def get_model_update(self):
        """Get model parameters for federated aggregation"""
        return self.model.state_dict()
    
    def apply_model_update(self, global_state_dict):
        """Apply global model update"""
        self.model.load_state_dict(global_state_dict)
        print("🔄 Đã cập nhật mô hình từ server trung tâm")
    
    def save_model(self, path=None):
        """Save the model"""
        save_path = path or self.model_path
        torch.save(self.model.state_dict(), f"{save_path}.pt")
        print(f"💾 Đã lưu mô hình FL vào {save_path}.pt")
    
    def load_model(self, path=None):
        """Load the model"""
        load_path = path or self.model_path
        try:
            self.model.load_state_dict(torch.load(f"{load_path}.pt"))
            print(f"📂 Đã tải mô hình FL từ {load_path}.pt")
        except Exception as e:
            print(f"⚠️ Không thể tải mô hình: {e}")

class FLCoordinator:
    """Federated Learning Coordinator (Central Server)"""
    def __init__(self, model_name="qwen2.5-coder:14b"):
        self.model_name = model_name
        self.global_model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.client_updates = []
    
    def aggregate_updates(self, client_states):
        """
        Aggregate model updates from clients using FedAvg
        
        :param client_states: List of state dicts from clients
        :return: Aggregated global state dict
        """
        if not client_states:
            return self.global_model.state_dict()
        
        print(f"🔄 Đang tổng hợp cập nhật từ {len(client_states)} client(s)")
        
        # Initialize with global model
        global_state = self.global_model.state_dict()
        
        # FedAvg: average all client updates
        for key in global_state.keys():
            global_state[key] = torch.stack([
                client_state[key].float() for client_state in client_states
            ]).mean(dim=0)
        
        print("✅ Đã tổng hợp cập nhật toàn cầu")
        return global_state
    
    def update_global_model(self, aggregated_state):
        """Update the global model with aggregated state"""
        self.global_model.load_state_dict(aggregated_state)
        print("🌐 Đã cập nhật mô hình toàn cầu")
    
    def save_global_model(self, path="/app/models/fl_global_model"):
        """Save the global model"""
        torch.save(self.global_model.state_dict(), f"{path}.pt")
        print(f"💾 Đã lưu mô hình toàn cầu vào {path}.pt")

# Example usage
if __name__ == "__main__":
    # Initialize FL client
    client = FLClient("client_001")
    
    # Collect some training examples (in practice, these would come from user interactions)
    client.collect_training_example(
        "Viết hàm Python để kiểm tra số nguyên tố",
        "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
        feedback_score=0.9
    )
    
    # Train locally
    client.local_train(epochs=2)
    
    # Save model
    client.save_model()
    
    # Example coordinator usage
    coordinator = FLCoordinator()
    # In practice, this would receive updates from multiple clients
    updates = [client.get_model_update()]
    aggregated = coordinator.aggregate_updates(updates)
    coordinator.update_global_model(aggregated)
    coordinator.save_global_model()