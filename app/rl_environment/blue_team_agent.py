import os
import numpy as np
import torch as th
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback
import logging
from .security_gym import SecurityEnv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainingCallback(BaseCallback):
    """
    Custom callback for plotting additional values in tensorboard.
    """
    def __init__(self, verbose=0):
        super(TrainingCallback, self).__init__(verbose)
    
    def _on_step(self) -> bool:
        # Log additional custom metrics
        return True

class BlueTeamAgent:
    """
    Blue Team Agent that learns optimal defense strategies using PPO
    """
    def __init__(self, cve_data=None, model_path="/app/models/blue_team_model"):
        """
        Initialize the Blue Team Agent
        
        :param cve_data: List of CVE dictionaries to use for training
        :param model_path: Path to save/load the model
        """
        self.cve_data = cve_data or []
        self.model_path = model_path
        
        # Create directory for model if it doesn't exist
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Initialize or load the model
        self.env = None
        self.model = None
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize or load the PPO model"""
        try:
            # Create a vectorized environment
            def make_env():
                return SecurityEnv(cve_data=self.cve_data)
            
            self.env = DummyVecEnv([make_env])
            
            # Try to load existing model, otherwise create new one
            if os.path.exists(f"{self.model_path}.zip"):
                logger.info(f"Loading existing model from {self.model_path}.zip")
                self.model = PPO.load(self.model_path, env=self.env)
            else:
                logger.info("Creating new PPO model")
                self.model = PPO(
                    "MlpPolicy",
                    self.env,
                    verbose=1,
                    learning_rate=3e-4,
                    n_steps=2048,
                    batch_size=64,
                    n_epochs=10,
                    gamma=0.99,
                    gae_lambda=0.95,
                    clip_range=0.2,
                    tensorboard_log="/app/rl_logs/"
                )
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def train(self, total_timesteps=10000, callback=None):
        """
        Train the agent
        
        :param total_timesteps: Number of timesteps to train for
        :param callback: Optional callback for training
        """
        try:
            logger.info(f"Starting training for {total_timesteps} timesteps")
            
            # Use default callback if none provided
            if callback is None:
                callback = TrainingCallback()
            
            # Train the model
            self.model.learn(
                total_timesteps=total_timesteps,
                callback=callback,
                reset_num_timesteps=False
            )
            
            # Save the model
            self.save()
            logger.info("Training completed and model saved")
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
    
    def predict(self, observation, deterministic=True):
        """
        Predict the best action for a given observation
        
        :param observation: Observation from the environment
        :param deterministic: Whether to use deterministic policy
        :return: Action and state
        """
        try:
            action, _states = self.model.predict(observation, deterministic=deterministic)
            return action, _states
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            # Return a safe default action (e.g., regular updates)
            return np.array([6]), None  # Action 6: Regular security updates
    
    def suggest_defense(self, cve_features):
        """
        Suggest a defense strategy for a given CVE
        
        :param cve_features: Dictionary containing CVE features
        :return: Suggested defense strategy description
        """
        try:
            # We need to create a temporary environment to get the observation
            # In a production system, we might want to precompute or cache this
            temp_env = SecurityEnv(cve_data=[cve_features])
            obs = temp_env.reset()
            
            # Get action from model
            action, _ = self.predict(obs)
            
            # Map action to defense strategy
            defense_strategies = {
                0: "Input validation and sanitization",
                1: "Output encoding",
                2: "Authentication and authorization checks",
                3: "Principle of least privilege",
                4: "Network segmentation",
                5: "Intrusion detection/prevention systems",
                6: "Regular security updates and patch management",
                7: "Security monitoring and logging",
                8: "Security awareness training",
                9: "Application firewall/WAF"
            }
            
            action_int = int(action) if hasattr(action, '__iter__') else action
            return defense_strategies.get(action_int, "Unknown defense strategy")
        except Exception as e:
            logger.error(f"Failed to suggest defense: {e}")
            return "Regular security updates and patch management"  # Fallback
    
    def save(self, path=None):
        """
        Save the model
        
        :param path: Path to save the model (defaults to self.model_path)
        """
        save_path = path if path is not None else self.model_path
        try:
            self.model.save(save_path)
            logger.info(f"Model saved to {save_path}.zip")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            raise
    
    def load(self, path=None):
        """
        Load the model
        
        :param path: Path to load the model from (defaults to self.model_path)
        """
        load_path = path if path is not None else self.model_path
        try:
            if os.path.exists(f"{load_path}.zip"):
                self.model = PPO.load(load_path, env=self.env)
                logger.info(f"Model loaded from {load_path}.zip")
            else:
                logger.warning(f"No model found at {load_path}.zip")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def close(self):
        """Clean up resources"""
        if self.env is not None:
            self.env.close()

# Example usage
if __name__ == "__main__":
    # Example CVE data for testing
    example_cve_data = [
        {
            'id': 'CVE-2026-1234',
            'cvss_score': 8.5,
            'exploit_maturity': 'proof-of-concept',
            'affected_software': ['webapp_v1', 'webapp_v2'],
            'cwe_ids': ['CWE-79', 'CWE-89'],
            'description': 'Cross-site scripting and SQL injection in web application'
        },
        {
            'id': 'CVE-2026-5678',
            'cvss_score': 9.8,
            'exploit_maturity': 'high',
            'affected_software': ['os_kernel_v5'],
            'cwe_ids': ['CWE-119', 'CWE-125'],
            'description': 'Buffer overflow in operating system kernel'
        }
    ]
    
    # Initialize agent
    agent = BlueTeamAgent(cve_data=example_cve_data)
    
    # Train for a short period (in practice, you would train much longer)
    agent.train(total_timesteps=500)
    
    # Test prediction
    test_cve = {
        'id': 'CVE-2026-9999',
        'cvss_score': 7.5,
        'exploit_maturity': 'low',
        'affected_software': ['network_device_v1'],
        'cwe_ids': ['CWE-22'],
        'description': 'Path traversal in network device'
    }
    
    defense = agent.suggest_defense(test_cve)
    print(f"Suggested defense for {test_cve['id']}: {defense}")
    
    # Clean up
    agent.close()