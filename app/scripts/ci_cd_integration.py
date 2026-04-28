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

class CICDIntegration:
    """CI/CD integration for automatic deployment of fixes"""
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
        self.github_token = get_env_safe("GITHUB_TOKEN")
        self.repo_name = get_env_safe("GITHUB_REPO")
        
    def check_github_status(self) -> bool:
        """Check if GitHub integration is properly configured"""
        return bool(self.github_token and self.repo_name)
    
    def get_github_client(self):
        """Get GitHub client if available"""
        if not self.check_github_status():
            return None
            
        try:
            from github import Github
            return Github(self.github_token)
        except ImportError:
            print("PyGithub not installed")
            return None
    
    def create_github_workflow(self, workflow_name: str, workflow_content: str) -> bool:
        """Create a GitHub Actions workflow"""
        try:
            github = self.get_github_client()
            if not github:
                return False
                
            repo = github.get_repo(self.repo_name)
            
            # Create .github/workflows directory if it doesn't exist
            workflows_path = ".github/workflows"
            try:
                repo.get_contents(workflows_path)
            except:
                # Create directory
                repo.create_file(
                    path=workflows_path + "/.gitkeep",
                    message="Create workflows directory",
                    content=""
                )
            
            # Create workflow file
            workflow_path = f"{workflows_path}/{workflow_name}.yml"
            try:
                # Check if file already exists
                contents = repo.get_contents(workflow_path)
                # Update existing file
                repo.update_file(
                    path=workflow_path,
                    message=f"Update {workflow_name} workflow",
                    content=workflow_content,
                    sha=contents.sha
                )
            except:
                # Create new file
                repo.create_file(
                    path=workflow_path,
                    message=f"Create {workflow_name} workflow",
                    content=workflow_content
                )
            
            return True
        except Exception as e:
            print(f"Error creating GitHub workflow: {e}")
            return False
    
    def create_auto_deploy_workflow(self) -> bool:
        """Create auto-deploy workflow for security fixes"""
        workflow_content = """
name: Auto Deploy Security Fixes

on:
  pull_request:
    branches: [ main, master ]
    types: [ closed ]

jobs:
  auto_deploy:
    if: github.event.pull_request.merged == true && contains(github.event.pull_request.title, 'Evo-AutoFix')
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      with:
        ref: ${{ github.event.pull_request.base.ref }}
        
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        
    - name: Run tests
      run: |
        python -m pytest
        
    - name: Deploy to production
      run: |
        echo "Deploying security fix..."
        # Add your deployment commands here
        # For example:
        # ./deploy.sh
        echo "Deployment completed"
        
    - name: Notify on success
      if: success()
      run: |
        echo "Security fix deployed successfully"
        
    - name: Notify on failure
      if: failure()
      run: |
        echo "Failed to deploy security fix"
"""
        
        return self.create_github_workflow("auto-deploy-security-fixes", workflow_content.strip())
    
    def create_security_scan_workflow(self) -> bool:
        """Create security scan workflow"""
        workflow_content = """
name: Security Scan

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install security tools
      run: |
        pip install bandit safety semgrep
        
    - name: Run Bandit security scan
      run: |
        bandit -r . -f json > bandit-report.json || true
        
    - name: Run Safety check
      run: |
        safety check --json > safety-report.json || true
        
    - name: Run Semgrep scan
      run: |
        semgrep --config=auto --json . > semgrep-report.json || true
        
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
          semgrep-report.json
          
    - name: Check for critical issues
      run: |
        # Add logic to check for critical issues and fail the build if needed
        echo "Security scan completed"
"""
        
        return self.create_github_workflow("security-scan", workflow_content.strip())
    
    def setup_ci_cd(self) -> Dict[str, bool]:
        """Setup CI/CD integration"""
        results = {
            "github_available": self.check_github_status(),
            "auto_deploy_created": False,
            "security_scan_created": False
        }
        
        if not results["github_available"]:
            print("GitHub integration not configured")
            return results
            
        # Create workflows
        results["auto_deploy_created"] = self.create_auto_deploy_workflow()
        results["security_scan_created"] = self.create_security_scan_workflow()
        
        return results

def main():
    """Main function to setup CI/CD integration"""
    print("Setting up CI/CD integration...")
    send_telegram("🔄 <b>THIẾT LẬP CI/CD:</b>\nĐang cấu hình tích hợp CI/CD cho tự động triển khai vá lỗi...")
    
    ci_cd = CICDIntegration()
    results = ci_cd.setup_ci_cd()
    
    if results["github_available"]:
        message = "🔄 <b>HOÀN TẤT THIẾT LẬP CI/CD:</b>\n"
        if results["auto_deploy_created"]:
            message += "✅ Đã tạo workflow tự động triển khai vá lỗi\n"
        if results["security_scan_created"]:
            message += "✅ Đã tạo workflow quét bảo mật tự động\n"
    else:
        message = "⚠️ <b>THIẾT LẬP CI/CD THẤT BẠI:</b>\nChưa cấu hình GitHub Token và Repository"
    
    send_telegram(message)
    print("CI/CD setup completed")

if __name__ == "__main__":
    main()