import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/app/.env", override=True)

def get_env_safe(key_name):
    val = os.getenv(key_name)
    if val:
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None

class AdvancedStaticAnalyzer:
    """Advanced static analysis with multiple tools integration"""
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
        self.tools = {
            "bandit": self._run_bandit,
            "semgrep": self._run_semgrep,
            "safety": self._run_safety,
            "sonarqube": self._run_sonarqube,
            "codeql": self._run_codeql,
            "eslint": self._run_eslint,
            "pylint": self._run_pylint
        }
    
    def _run_bandit(self) -> Dict:
        """Run Bandit security analyzer"""
        try:
            # Check if bandit is installed
            result = subprocess.run(
                ["bandit", "--version"], 
                capture_output=True, 
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode != 0:
                print("Bandit not installed, installing...")
                subprocess.run(
                    ["pip", "install", "bandit"], 
                    check=True,
                    cwd=str(self.workspace_path)
                )
            
            # Run bandit on all Python files
            cmd = ["bandit", "-r", ".", "-f", "json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"results": [], "errors": [result.stdout]}
            else:
                return {"results": [], "errors": [result.stderr]}
                
        except Exception as e:
            return {"results": [], "errors": [str(e)]}
    
    def _run_semgrep(self) -> Dict:
        """Run Semgrep security analyzer"""
        try:
            # Check if semgrep is installed
            result = subprocess.run(
                ["semgrep", "--version"], 
                capture_output=True, 
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode != 0:
                print("Semgrep not installed, installing...")
                subprocess.run(
                    ["pip", "install", "semgrep"], 
                    check=True,
                    cwd=str(self.workspace_path)
                )
            
            # Run semgrep with security rules
            cmd = ["semgrep", "--config=auto", "--json", "."]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"results": [], "errors": [result.stdout]}
            else:
                return {"results": [], "errors": [result.stderr]}
                
        except Exception as e:
            return {"results": [], "errors": [str(e)]}
    
    def _run_safety(self) -> Dict:
        """Run Safety to check for vulnerable dependencies"""
        try:
            # Check if safety is installed
            result = subprocess.run(
                ["safety", "--version"], 
                capture_output=True, 
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode != 0:
                print("Safety not installed, installing...")
                subprocess.run(
                    ["pip", "install", "safety"], 
                    check=True,
                    cwd=str(self.workspace_path)
                )
            
            # Run safety check
            cmd = ["safety", "check", "--json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"results": [], "errors": [result.stdout]}
            else:
                return {"results": [], "errors": [result.stderr]}
                
        except Exception as e:
            return {"results": [], "errors": [str(e)]}
    
    def _run_sonarqube(self) -> Dict:
        """Run SonarQube analysis"""
        try:
            # Check if sonar-scanner is available
            result = subprocess.run(
                ["sonar-scanner", "--version"], 
                capture_output=True, 
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode != 0:
                print("SonarQube scanner not found")
                return {"results": [], "errors": ["SonarQube scanner not found"]}
            
            # Run SonarQube analysis
            # This is a simplified version - in practice, you would need to configure SonarQube properly
            cmd = ["sonar-scanner"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.workspace_path)
            )
            
            return {"results": result.stdout, "errors": [] if result.returncode == 0 else [result.stderr]}
        except Exception as e:
            return {"results": [], "errors": [str(e)]}
    
    def _run_codeql(self) -> Dict:
        """Run CodeQL analysis"""
        try:
            # Check if CodeQL CLI is available
            result = subprocess.run(
                ["codeql", "--version"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                print("CodeQL CLI not found")
                return {"results": [], "errors": ["CodeQL CLI not found"]}
            
            # This is a simplified version - in practice, CodeQL requires more setup
            # For now, we'll just check if it's available
            return {"results": "CodeQL is available", "errors": []}
        except Exception as e:
            return {"results": [], "errors": [str(e)]}
    
    def _run_eslint(self) -> Dict:
        """Run ESLint for JavaScript/TypeScript analysis"""
        try:
            # Check if eslint is installed
            result = subprocess.run(
                ["npx", "eslint", "--version"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                print("ESLint not found, installing...")
                subprocess.run(
                    ["npm", "install", "-g", "eslint"], 
                    check=True
                )
            
            # Run ESLint
            cmd = ["npx", "eslint", "."]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            return {"results": result.stdout, "errors": [] if result.returncode == 0 else [result.stderr]}
        except Exception as e:
            return {"results": [], "errors": [str(e)]}
    
    def _run_pylint(self) -> Dict:
        """Run Pylint for Python code analysis"""
        try:
            # Check if pylint is installed
            result = subprocess.run(
                ["pylint", "--version"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                print("Pylint not installed, installing...")
                subprocess.run(
                    ["pip", "install", "pylint"], 
                    check=True
                )
            
            # Run Pylint
            cmd = ["pylint", "."]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            return {"results": result.stdout, "errors": [] if result.returncode == 0 else [result.stderr]}
        except Exception as e:
            return {"results": [], "errors": [str(e)]}
    
    def run_advanced_analysis(self, tools_to_run: List[str] = None) -> Dict:
        """Run advanced static analysis with multiple tools"""
        if tools_to_run is None:
            tools_to_run = list(self.tools.keys())
        
        results = {}
        total_issues = 0
        
        for tool_name in tools_to_run:
            if tool_name in self.tools:
                print(f"Running {tool_name} analysis...")
                tool_results = self.tools[tool_name]()
                results[tool_name] = tool_results
                
                # Count issues
                if "results" in tool_results and tool_results["results"]:
                    total_issues += len(tool_results["results"]) if isinstance(tool_results["results"], list) else 1
        
        return results

def main():
    """Main function to run advanced static analysis"""
    print("Running advanced static analysis...")
    
    # Create analyzer instance
    analyzer = AdvancedStaticAnalyzer()
    
    # Run analysis with all tools
    results = analyzer.run_advanced_analysis()
    
    # Print summary
    print("Advanced static analysis completed:")
    for tool, result in results.items():
        if "results" in result and result["results"]:
            issues = result["results"] if isinstance(result["results"], list) else [result["results"]]
            print(f"- {tool}: {len(issues) if isinstance(issues, list) else 1} issues found")
        else:
            print(f"- {tool}: No issues found")
    
    print("Analysis complete. Check results above.")

if __name__ == "__main__":
    main()