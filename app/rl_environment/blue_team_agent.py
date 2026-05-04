import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import logging

from .security_gym import SecurityEnv

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("RL_MODEL_PATH", "/app/models/blue_team_model")


class BlueTeamAgent:
    def __init__(self, cve_data=None):
        self.cve_data = cve_data or []
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

        def make_env():
            return SecurityEnv(cve_data=self.cve_data)

        self.env = DummyVecEnv([make_env])

        if os.path.exists(f"{MODEL_PATH}.zip"):
            logger.info(f"Loading RL model from {MODEL_PATH}.zip")
            self.model = PPO.load(MODEL_PATH, env=self.env)
        else:
            logger.info("Creating new PPO model")
            self.model = PPO(
                "MlpPolicy", self.env, verbose=0,
                learning_rate=3e-4, n_steps=2048, batch_size=64,
                n_epochs=10, gamma=0.99, gae_lambda=0.95, clip_range=0.2
            )

    def train(self, total_timesteps=10000):
        logger.info(f"Training RL agent for {total_timesteps} timesteps")
        self.model.learn(total_timesteps=total_timesteps)
        self.model.save(MODEL_PATH)
        logger.info("RL training complete")

    def suggest_defense(self, cve_features: dict) -> dict:
        temp_env = SecurityEnv(cve_data=[cve_features])
        obs, _ = temp_env.reset()
        action, _ = self.model.predict(obs, deterministic=True)
        action_int = int(action)

        strategies = SecurityEnv.DEFENSE_STRATEGIES
        return {
            "action": action_int,
            "strategy": strategies.get(action_int, "Unknown"),
            "cve_id": cve_features.get("id", "unknown")
        }

    def close(self):
        self.env.close()


_agent_instance = None


def get_rl_agent():
    global _agent_instance
    if _agent_instance is None:
        try:
            _agent_instance = BlueTeamAgent()
        except Exception as e:
            logger.warning(f"RL agent init failed: {e}")
            _agent_instance = None
    return _agent_instance
