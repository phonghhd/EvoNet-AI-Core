import os
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random


class SecurityEnv(gym.Env):
    metadata = {'render_modes': ['human']}

    DEFENSE_STRATEGIES = {
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

    CWE_TO_BEST_ACTION = {
        'CWE-79': 1, 'CWE-89': 0, 'CWE-20': 0, 'CWE-22': 0,
        'CWE-23': 0, 'CWE-78': 0, 'CWE-94': 0, 'CWE-119': 6,
        'CWE-125': 6, 'CWE-269': 3, 'CWE-287': 2, 'CWE-352': 2,
        'CWE-434': 0, 'CWE-502': 0, 'CWE-611': 0, 'CWE-918': 4,
    }

    def __init__(self, cve_data=None, max_steps=10):
        super().__init__()
        self.cve_data = cve_data or []
        self.max_steps = max_steps
        self.action_space = spaces.Discrete(10)
        self.observation_space = spaces.Box(low=0, high=1, shape=(20,), dtype=np.float32)
        self.state = None
        self.steps_done = 0
        self.current_cve = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps_done = 0
        self.current_cve = random.choice(self.cve_data) if self.cve_data else self._generate_dummy_cve()
        self.state = self._cve_to_observation(self.current_cve)
        return self.state, {}

    def step(self, action):
        self.steps_done += 1
        reward = self._calculate_reward(action)
        done = self.steps_done >= self.max_steps
        if not done:
            self.state = self._cve_to_observation(self.current_cve) * random.uniform(0.8, 1.2)
            self.state = np.clip(self.state + np.random.normal(0, 0.05, self.state.shape), 0, 1)
        info = {
            'cve_id': self.current_cve.get('id', 'unknown'),
            'defense_strategy': self.DEFENSE_STRATEGIES.get(action, "Unknown"),
        }
        return self.state, reward, done, False, info

    def _calculate_reward(self, action):
        reward = 0.1
        cwe_ids = self.current_cve.get('cwe_ids', [])
        exploit_maturity = self.current_cve.get('exploit_maturity', 'low')

        for cwe in cwe_ids:
            best_action = self.CWE_TO_BEST_ACTION.get(cwe)
            if best_action is not None:
                if action == best_action:
                    reward += 0.5
                elif abs(action - best_action) <= 2:
                    reward += 0.2

        if exploit_maturity in ['high', 'proof-of-concept'] and action == 5:
            reward += 0.3
        if exploit_maturity != 'zero-day' and action == 6:
            reward += 0.3

        return max(-1.0, min(1.0, reward))

    def _cve_to_observation(self, cve):
        obs = np.zeros(20, dtype=np.float32)
        obs[0] = min(cve.get('cvss_score', 5.0) / 10.0, 1.0)
        maturity_map = {'none': 0.0, 'low': 0.33, 'proof-of-concept': 0.66, 'high': 1.0}
        obs[1] = maturity_map.get(cve.get('exploit_maturity', 'low'), 0.33)
        affected_count = len(cve.get('affected_software', []))
        obs[2] = min(affected_count / 10.0, 1.0)

        cwe_mapping = {
            'CWE-79': 5, 'CWE-89': 6, 'CWE-22': 7, 'CWE-20': 8,
            'CWE-119': 9, 'CWE-125': 10, 'CWE-269': 11, 'CWE-287': 12,
            'CWE-352': 13, 'CWE-434': 14
        }
        for cwe in cve.get('cwe_ids', []):
            if cwe in cwe_mapping:
                obs[cwe_mapping[cwe]] = 1.0

        for i in range(15, 20):
            obs[i] = random.uniform(0.1, 0.9)

        return np.clip(obs, 0.0, 1.0)

    def _generate_dummy_cve(self):
        cwe_list = ['CWE-79', 'CWE-89', 'CWE-22', 'CWE-20', 'CWE-119', 'CWE-269', 'CWE-287']
        return {
            'id': f'CVE-2026-{random.randint(1000, 9999)}',
            'cvss_score': random.uniform(1.0, 10.0),
            'exploit_maturity': random.choice(['none', 'low', 'proof-of-concept', 'high']),
            'affected_software': [f'software_{i}' for i in range(random.randint(1, 8))],
            'cwe_ids': random.sample(cwe_list, random.randint(1, 3)),
        }
