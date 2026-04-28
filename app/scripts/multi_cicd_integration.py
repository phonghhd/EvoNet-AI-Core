import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/app/.env", override=True)

def get_env_safe(key_name):
    val = os.getenv(key_name)
    if val:
        return val.strip().strip('\'"').replace('\n', '').replace('\r', '')
    return None

class MultiCICDIntegration:
    """Multi-platform CI/CD integration system"""
    
    def __init__(self):
        self.github_token = get_env_safe("GITHUB_TOKEN")
        self.gitlab_token = get_env_safe("GITLAB_TOKEN")
        self.jenkins_url = get_env_safe("JENKINS_URL")
        self.jenkins_username = get_env_safe("JENKINS_USERNAME")
        self.jenkins_token = get_env_safe("JENKINS_TOKEN")
        
    def create_github_workflow(self, workflow_name: str, workflow_content: str) -> bool:
        """Create GitHub Actions workflow"""
        try:
            if not self.github_token:
                print("GitHub token not configured")
                return False
                
            from github import Github
            g = Github(self.github_token)
            
            # Get repository (assuming it's in an environment variable)
            repo_name = os.getenv("GITHUB_REPO")
            if not repo_name:
                print("GitHub repository not configured")
                return False
                
            repo = g.get_repo(repo_name)
            
            # Create .github/workflows directory if it doesn't exist
            workflows_path = ".github/workflows"
            try:
                repo.get_contents(workflows_path)
            except:
                # Create directory
                repo.create_file(
                    path=f"{workflows_path}/.gitkeep",
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
    
    def create_gitlab_ci_config(self, config_content: str) -> bool:
        """Create GitLab CI configuration"""
        try:
            if not self.gitlab_token:
                print("GitLab token not configured")
                return False
            
            # Get GitLab project ID (assuming it's in an environment variable)
            project_id = os.getenv("GITLAB_PROJECT_ID")
            if not project_id:
                print("GitLab project ID not configured")
                return False
            
            gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
            
            # Create or update .gitlab-ci.yml
            url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/files/.gitlab-ci.yml"
            
            headers = {
                "PRIVATE-TOKEN": self.gitlab_token,
                "Content-Type": "application/json"
            }
            
            # Check if file exists
            response = requests.get(f"{url}?ref=main", headers=headers)
            
            if response.status_code == 200:
                # Update existing file
                data = {
                    "branch": "main",
                    "content": config_content,
                    "commit_message": "Update GitLab CI configuration"
                }
                response = requests.put(url, headers=headers, json=data)
            else:
                # Create new file
                data = {
                    "branch": "main",
                    "content": config_content,
                    "commit_message": "Add GitLab CI configuration",
                    "encoding": "text"
                }
                response = requests.post(url, headers=headers, json=data)
            
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error creating GitLab CI config: {e}")
            return False
    
    def create_jenkins_pipeline(self, pipeline_name: str, pipeline_script: str) -> bool:
        """Create Jenkins pipeline"""
        try:
            if not self.jenkins_url or not self.jenkins_username or not self.jenkins_token:
                print("Jenkins credentials not configured")
                return False
            
            # Create Jenkins job using REST API
            url = f"{self.jenkins_url}/createItem?name={pipeline_name}"
            
            headers = {
                "Content-Type": "text/xml",
                "Authorization": f"Basic {self._get_jenkins_auth()}"
            }
            
            # Jenkins job configuration XML
            config_xml = f"""<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job@2.40">
  <description>Automated security pipeline for {pipeline_name}</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <hudson.model.ParametersDefinitionProperty>
      <parameterDefinitions>
        <hudson.model.StringParameterDefinition>
          <name>BRANCH</name>
          <defaultValue>main</defaultValue>
          <trim>true</trim>
        </hudson.model.StringParameterDefinition>
      </parameterDefinitions>
    </hudson.model.ParametersDefinitionProperty>
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps@2.90">
    <script>{pipeline_script}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>"""
            
            response = requests.post(url, headers=headers, data=config_xml)
            return response.status_code == 200
        except Exception as e:
            print(f"Error creating Jenkins pipeline: {e}")
            return False
    
    def _get_jenkins_auth(self) -> str:
        """Get Jenkins authentication string"""
        import base64
        auth_string = f"{self.jenkins_username}:{self.jenkins_token}"
        return base64.b64encode(auth_string.encode()).decode()
    
    def setup_all_platforms(self) -> Dict[str, bool]:
        """Setup CI/CD integration for all available platforms"""
        results = {
            "github": False,
            "gitlab": False,
            "jenkins": False
        }
        
        # GitHub Actions workflow
        github_workflow = """
name: Security Pipeline

on:
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
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        
    - name: Run security analysis
      run: |
        python app/scripts/static_analyzer.py
        
    - name: Run tests
      run: |
        python -m pytest
        
    - name: Auto-fix security issues
      if: failure()
      run: |
        python app/scripts/evo_autofix.py
"""
        
        if self.github_token:
            results["github"] = self.create_github_workflow("security-pipeline", github_workflow.strip())
        
        # GitLab CI configuration
        gitlab_config = """
stages:
  - security-analysis
  - test
  - deploy

variables:
  PYTHON_VERSION: "3.9"

before_script:
  - apt-get update && apt-get install -y python3 python3-pip
  - pip3 install -r requirements.txt

security-analysis:
  stage: security-analysis
  script:
    - python app/scripts/static_analyzer.py
  only:
    - main
    - merge_requests

test:
  stage: test
  script:
    - python -m pytest
  only:
    - main
    - merge_requests

auto-deploy:
  stage: deploy
  script:
    - echo "Deploying security fixes..."
    - python app/scripts/auto_patch_generator.py
  only:
    - main
"""
        
        if self.gitlab_token:
            results["gitlab"] = self.create_gitlab_ci_config(gitlab_config.strip())
        
        # Jenkins pipeline script
        jenkins_script = """
pipeline {
    agent any
    
    stages {
        stage('Security Analysis') {
            steps {
                sh 'python app/scripts/static_analyzer.py'
            }
        }
        
        stage('Test') {
            steps {
                sh 'python -m pytest'
            }
        }
        
        stage('Auto-fix Security Issues') {
            steps {
                sh 'python app/scripts/evo_autofix.py'
            }
            post {
                failure {
                    sh 'echo "Security fix failed, manual intervention required"'
                }
            }
        }
    }
}
"""
        
        if self.jenkins_url and self.jenkins_username and self.jenkins_token:
            results["jenkins"] = self.create_jenkins_pipeline("security-pipeline", jenkins_script)
        
        return results

def main():
    """Main function to setup multi-platform CI/CD integration"""
    print("Setting up multi-platform CI/CD integration...")
    
    cicd = MultiCICDIntegration()
    results = cicd.setup_all_platforms()
    
    print("CI/CD integration results:")
    for platform, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {platform.upper()}: {status}")

if __name__ == "__main__":
    main()