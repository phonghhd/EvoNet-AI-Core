import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/app/.env", override=True)

def get_env_safe(key_name):
    val = os.getenv(key_name)
    if val:
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None

def send_telegram(msg):
    token = get_env_safe("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_safe("TELEGRAM_CHAT_ID")
    if not token or not chat_id: 
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try: 
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

class StaticAnalyzer:
    """Static code analyzer for security vulnerabilities"""
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
        self.tools = {
            "bandit": self._run_bandit,
            "semgrep": self._run_semgrep,
            "safety": self._run_safety
        }
    
    def _run_bandit(self) -> Dict[str, Any]:
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
    
    def _run_semgrep(self) -> Dict[str, Any]:
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
    
    def _run_safety(self) -> Dict[str, Any]:
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
    
    def analyze(self, tools_to_run: List[str] = None) -> Dict[str, Any]:
        """
        Run static analysis tools on the codebase
        
        :param tools_to_run: List of specific tools to run (default: all)
        :return: Dictionary with analysis results
        """
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
                if "results" in tool_results:
                    total_issues += len(tool_results["results"])
                elif tool_name == "safety" and "vulnerabilities" in tool_results:
                    total_issues += len(tool_results["vulnerabilities"])
        
        # Send summary to Telegram
        send_telegram(f"🔍 <b>PHÂN TÍCH MÃ NGUỒN TĨNH:</b>\nĐã phát hiện {total_issues} vấn đề tiềm ẩn trong codebase.")
        
        return results

def main():
    """Main function to run static analysis"""
    print("Starting static code analysis...")
    send_telegram("🔍 <b>BẮT ĐẦU PHÂN TÍCH MÃ NGUỒN TĨNH:</b>\nĐang kiểm tra codebase để phát hiện lỗi tiềm ẩn...")
    
    analyzer = StaticAnalyzer()
    results = analyzer.analyze()
    
    # Print summary
    print("Static analysis completed:")
    for tool, result in results.items():
        if "results" in result and result["results"]:
            print(f"- {tool}: {len(result['results'])} issues found")
        elif tool == "safety" and "vulnerabilities" in result:
            print(f"- {tool}: {len(result['vulnerabilities'])} vulnerabilities found")
        else:
            print(f"- {tool}: No issues found")
    
    print("Analysis complete. Check results above.")
    send_telegram("✅ <b>HOÀN TẤT PHÂN TÍCH MÃ NGUỒN TĨNH:</b>\nĐã hoàn tất kiểm tra codebase. Kiểm tra kết quả trong logs.")

if __name__ == "__main__":
    main()