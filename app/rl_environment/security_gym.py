import gym
from gym import spaces
import numpy as np
import random
import json

class SecurityEnv(gym.Env):
    """
    Custom Environment for Cybersecurity Defense that follows gym interface
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, cve_data=None, max_steps=10):
        super(SecurityEnv, self).__init__()
        
        # Store CVE data for the environment
        self.cve_data = cve_data or []
        self.max_steps = max_steps
        
        # Define action and observation space
        # Actions: 0-9 representing different defense strategies
        self.action_space = spaces.Discrete(10)
        
        # Observation: 20-dimensional vector representing CVE characteristics
        # This could include: CVSS score, exploit availability, affected systems count, etc.
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(20,), dtype=np.float32
        )
        
        # Initialize state
        self.state = None
        self.steps_done = 0
        self.current_cve = None
        
        # Define defense strategy mapping (action -> description)
        self.defense_strategies = {
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
        
    def reset(self):
        """Reset the environment to initial state"""
        self.steps_done = 0
        
        # Select a random CVE from the dataset
        if self.cve_data:
            self.current_cve = random.choice(self.cve_data)
        else:
            # Generate a dummy CVE if no data provided
            self.current_cve = self._generate_dummy_cve()
        
        # Convert CVE features to observation vector
        self.state = self._cve_to_observation(self.current_cve)
        
        return self.state
    
    def step(self, action):
        """Execute one time step within the environment"""
        self.steps_done += 1
        
        # Calculate reward based on action effectiveness
        reward = self._calculate_reward(action)
        
        # Check if episode is done
        done = self.steps_done >= self.max_steps
        
        # For simplicity, we'll reset the state after each step in this example
        # In a more complex environment, the state would evolve based on actions
        if not done:
            # Partially reset state to simulate ongoing assessment
            self.state = self._cve_to_observation(self.current_cve) * random.uniform(0.8, 1.2)
            # Add some noise to simulate changing conditions
            self.state = np.clip(self.state + np.random.normal(0, 0.05, self.state.shape), 0, 1)
        else:
            # Final state
            self.state = self._cve_to_observation(self.current_cve)
        
        # Additional info
        info = {
            'cve_id': self.current_cve.get('id', 'unknown'),
            'action_taken': action,
            'defense_strategy': self.defense_strategies.get(action, "Unknown"),
            'steps_done': self.steps_done
        }
        
        return self.state, reward, done, info
    
    def _calculate_reward(self, action):
        """
        Calculate reward based on how effective the defense strategy is
        for the current CVE
        """
        # Base reward
        reward = 0.1
        
        # Get CVE characteristics
        cwe_ids = self.current_cve.get('cwe_ids', [])
        exploit_maturity = self.current_cve.get('exploit_maturity', 'low')
        affected_software_count = len(self.current_cve.get('affected_software', []))
        
        # Reward based on action appropriateness
        if action == 0:  # Input validation and sanitization
            # Good for injection flaws (XSS, SQLi, etc.)
            if any(cwe in ['CWE-79', 'CWE-89', 'CWE-20', 'CWE-22', 'CWE-23'] for cwe in cwe_ids):
                reward += 0.5
            # Less effective for other types
            elif 'CWE-119' in cwe_ids or 'CWE-125' in cwe_ids:  # Buffer errors
                reward += 0.1
            else:
                reward += 0.2
                
        elif action == 1:  # Output encoding
            # Excellent for XSS
            if 'CWE-79' in cwe_ids:
                reward += 0.6
            # Somewhat useful for other injection
            elif any(cwe in ['CWE-89', 'CWE-78', 'CWE-93'] for cwe in cwe_ids):
                reward += 0.3
            else:
                reward += 0.1
                
        elif action == 2:  # Authentication and authorization checks
            # Good for auth bypass, privilege escalation
            if any(cwe in ['CWE-287', 'CWE-284', 'CWE-269', 'CWE-664'] for cwe in cwe_ids):
                reward += 0.5
            else:
                reward += 0.2
                
        elif action == 3:  # Principle of least privilege
            # Good for privilege escalation
            if any(cwe in ['CWE-269', 'CWE-250', 'CWE-255', 'CWE-266'] for cwe in cwe_ids):
                reward += 0.5
            else:
                reward += 0.2
                
        elif action == 4:  # Network segmentation
            # Good for network-related exploits
            if any(cwe in ['CWE-200', 'CWE-215', 'CWE-610', 'CWE-94'] for cwe in cwe_ids):
                reward += 0.4
            # Also useful for limiting blast radius
            elif exploit_maturity in ['high', 'proof-of-concept']:
                reward += 0.3
            else:
                reward += 0.1
                
        elif action == 5:  # Intrusion detection/prevention systems
            # Good for known exploit patterns
            if exploit_maturity in ['high', 'proof-of-concept']:
                reward += 0.5
            # Less effective for zero-days
            elif exploit_maturity == 'low':
                reward += 0.2
            else:
                reward += 0.3
                
        elif action == 6:  # Regular security updates and patch management
            # Always good, especially for known vulnerabilities
            if exploit_maturity != 'zero-day':
                reward += 0.4
            else:
                reward += 0.1  # Less effective for true zero-days
                
        elif action == 7:  # Security monitoring and logging
            # Good for detection and forensics
            reward += 0.3
            # Bonus if we have many affected systems (more to monitor)
            if affected_software_count > 5:
                reward += 0.2
                
        elif action == 8:  # Security awareness training
            # Good for social engineering
            if any(cwe in ['CWE-250', 'CWE-352', 'CWE-342', 'CWE-346'] for cwe in cwe_ids):
                reward += 0.4
            else:
                reward += 0.1
                
        elif action == 9:  # Application firewall/WAF
            # Good for web application attacks
            if any(cwe in ['CWE-79', 'CWE-89', 'CWE-22', 'CWE-23', 'CWE-98', 'CWE-94'] for cwe in cwe_ids):
                reward += 0.5
            else:
                reward += 0.2
        
        # Penalty for ineffective actions based on exploit maturity
        if exploit_maturity == 'zero-day' and action in [0, 1, 2, 3, 4, 8, 9]:
            # Zero-days are hard to defend with specific technical controls
            reward *= 0.7
        elif exploit_maturity == 'high' and action in [6]:  # Patching
            # High maturity exploits often have patches available
            reward *= 1.2
            
        # Normalize reward to reasonable range
        reward = max(-1.0, min(1.0, reward))
        
        return reward
    
    def _cve_to_observation(self, cve):
        """
        Convert CVE data to a normalized observation vector
        """
        obs = np.zeros(20, dtype=np.float32)
        
        # Feature 0-1: CVSS score (normalized 0-1)
        cvss_score = cve.get('cvss_score', 5.0)  # Default medium severity
        obs[0] = min(cvss_score / 10.0, 1.0)
        
        # Feature 2: Exploit maturity (0: none, 0.33: low, 0.66: proof-of-concept, 1.0: high)
        maturity_map = {
            'none': 0.0,
            'low': 0.33,
            'proof-of-concept': 0.66,
            'high': 1.0
        }
        obs[1] = maturity_map.get(cve.get('exploit_maturity', 'low'), 0.33)
        
        # Feature 3-4: Affected software count (normalized)
        affected_count = len(cve.get('affected_software', []))
        obs[2] = min(affected_count / 10.0, 1.0)  # Assume max 10 for normalization
        obs[3] = min(affected_count / 50.0, 1.0)  # Different scale
        
        # Feature 5-6: Publication age (newer = higher value)
        # In a real implementation, we would calculate days since publication
        # For now, use a placeholder
        obs[4] = random.uniform(0.3, 0.8)  # Placeholder
        
        # Feature 7-8: CWE prevalence (simplified)
        cwe_ids = cve.get('cwe_ids', [])
        # Map some common CWEs to indices
        cwe_mapping = {
            'CWE-79': 5,    # XSS
            'CWE-89': 6,    # SQL Injection
            'CWE-22': 7,    # Path Traversal
            'CWE-20': 8,    # Input Validation
            'CWE-119': 9,   # Buffer Errors
            'CWE-125': 10,  # Buffer Under-read
            'CWE-269': 11,  # Privilege Escalation
            'CWE-287': 12,  # Authentication Issues
            'CWE-352': 13,  # CSRF
            'CWE-434': 14   # Unrestricted Upload
        }
        
        for cwe in cwe_ids:
            if cwe in cwe_mapping:
                idx = cwe_mapping[cwe]
                obs[idx] = 1.0
        
        # Feature 15-19: Additional characteristics (placeholder for more sophisticated features)
        # In a real implementation, these would be derived from CVE data
        for i in range(15, 20):
            obs[i] = random.uniform(0.1, 0.9)  # Placeholder values
            
        # Ensure we don't exceed bounds
        obs = np.clip(obs, 0.0, 1.0)
        
        return obs
    
    def _generate_dummy_cve(self):
        """Generate a dummy CVE for testing when no real data is available"""
        cwe_list = ['CWE-79', 'CWE-89', 'CWE-22', 'CWE-20', 'CWE-119', 'CWE-269', 'CWE-287']
        maturity_list = ['none', 'low', 'proof-of-concept', 'high']
        
        return {
            'id': f'CVE-2026-{random.randint(1000, 9999)}',
            'cvss_score': random.uniform(1.0, 10.0),
            'exploit_maturity': random.choice(maturity_list),
            'affected_software': [f'software_{i}' for i in range(random.randint(1, 8))],
            'cwe_ids': random.sample(cwe_list, random.randint(1, 3)),
            'description': 'Generated dummy CVE for training environment'
        }
    
    def render(self, mode='human'):
        """Render the environment"""
        if self.current_cve:
            print(f"Current CVE: {self.current_cve.get('id', 'Unknown')}")
            print(f"CVSS Score: {self.current_cve.get('cvss_score', 'N/A')}")
            print(f"Exploit Maturity: {self.current_cve.get('exploit_maturity', 'N/A')}")
            print(f"CWE IDs: {', '.join(self.current_cve.get('cwe_ids', []))}")
            print(f"Step: {self.steps_done}/{self.max_steps}")
            if self.steps_done > 0:
                print(f"Last action: {self.defense_strategies.get(getattr(self, 'last_action', None), 'Unknown')}")
        else:
            print("Environment not initialized")
    
    def close(self):
        """Clean up resources"""
        pass