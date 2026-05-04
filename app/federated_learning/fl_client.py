import os
import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.utils.data import Dataset, DataLoader
import hashlib
from datetime import datetime

DEFAULT_MODEL = os.getenv("FL_MODEL_NAME", "Qwen/Qwen2.5-Coder-1.5B-Instruct")
DEFAULT_MODEL_DIR = os.getenv("FL_MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "models"))


class FLDataset(Dataset):
    def __init__(self, data_list, tokenizer, max_length=512):
        self.data = data_list
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        text = f"Human: {item.get('prompt', '')}\nAssistant: {item.get('response', '')}"
        encoding = self.tokenizer(
            text, truncation=True, padding='max_length',
            max_length=self.max_length, return_tensors='pt'
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten()
        }


class FLClient:
    def __init__(self, client_id, model_name=None, model_path=None):
        self.client_id = client_id
        self.model_name = model_name or DEFAULT_MODEL
        self.model_path = model_path or os.path.join(DEFAULT_MODEL_DIR, f"fl_model_{client_id}")
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.local_dataset = []
        self._load_model()

    def _load_model(self):
        path = f"{self.model_path}.pt"
        if os.path.exists(path):
            try:
                self.model.load_state_dict(torch.load(path, map_location='cpu'))
                print(f"Loaded FL model from {path}")
            except Exception as e:
                print(f"Cannot load FL model: {e}")

    def collect_training_example(self, prompt, response, feedback_score=1.0):
        if feedback_score >= 0.7:
            self.local_dataset.append({
                'prompt': prompt, 'response': response,
                'feedback_score': feedback_score,
                'timestamp': datetime.now().isoformat(),
                'hash': hashlib.md5(f"{prompt}{response}".encode()).hexdigest()
            })

    def local_train(self, epochs=1, learning_rate=5e-5, batch_size=4):
        if not self.local_dataset:
            return None

        dataset = FLDataset(self.local_dataset, self.tokenizer)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)
        self.model.train()

        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                optimizer.zero_grad()
                outputs = self.model(
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask'],
                    labels=batch['input_ids']
                )
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            print(f"FL Epoch {epoch+1}/{epochs} - Loss: {total_loss / max(len(dataloader), 1):.4f}")

        self.model.eval()
        return self.model.state_dict()

    def get_model_update(self):
        return self.model.state_dict()

    def apply_model_update(self, global_state_dict):
        self.model.load_state_dict(global_state_dict)

    def save_model(self, path=None):
        save_path = path or self.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save(self.model.state_dict(), f"{save_path}.pt")


class FLCoordinator:
    def __init__(self, model_name=None):
        self.model_name = model_name or DEFAULT_MODEL
        self.global_model = AutoModelForCausalLM.from_pretrained(self.model_name)

    def aggregate_updates(self, client_states):
        if not client_states:
            return self.global_model.state_dict()
        global_state = self.global_model.state_dict()
        for key in global_state.keys():
            global_state[key] = torch.stack([cs[key].float() for cs in client_states]).mean(dim=0)
        return global_state

    def update_global_model(self, aggregated_state):
        self.global_model.load_state_dict(aggregated_state)

    def save_global_model(self, path=None):
        save_path = path or os.path.join(DEFAULT_MODEL_DIR, "fl_global_model")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save(self.global_model.state_dict(), f"{save_path}.pt")
