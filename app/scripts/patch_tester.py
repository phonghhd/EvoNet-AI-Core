import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

class PatchTester:
    def __init__(self, workspace_path="./workspace"):
        self.workspace_path = Path(workspace_path)
        # Create workspace if it doesn't exist
        self.workspace_path.mkdir(exist_ok=True)
    
    def run_tests(self, file_path=None, test_command=None):
        """
        Run tests to validate a patch
        
        :param file_path: Path to the file being tested (optional)
        :param test_command: Custom test command to run (optional)
        :return: dict with test results
        """
        try:
            # If custom test command is provided, use it
            if test_command:
                print(f"🏃 Đang chạy lệnh kiểm thử tùy chỉnh: {test_command}")
                result = subprocess.run(
                    test_command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=300,  # 5 minutes timeout
                    cwd=str(self.workspace_path)
                )
                return {
                    'passed': result.returncode == 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            
            # Default test strategy: run pytest if available
            print("🏃 Đang chạy kiểm thử mặc định (pytest)...")
            
            # Check if pytest is available
            result = subprocess.run(
                ["which", "pytest"], 
                capture_output=True, 
                text=True,
                cwd=str(self.workspace_path)
            )
            
            if result.returncode == 0:
                # Run pytest
                cmd = ["pytest", "-v"]
                if file_path:
                    # Run tests for specific file only
                    cmd.extend([str(file_path)])
                else:
                    # Run all tests
                    cmd.extend(["--tb=short"])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout
                    cwd=str(self.workspace_path)
                )
                
                return {
                    'passed': result.returncode == 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            else:
                # Fallback to basic Python syntax check
                print("⚠️ Pytest không khả dụng, kiểm tra cú pháp Python cơ bản...")
                if file_path and file_path.exists():
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(file_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return {
                        'passed': result.returncode == 0,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                else:
                    # No specific file to check, assume tests pass
                    print("⚠️ Không có file cụ thể để kiểm tra, giả định kiểm thử thành công")
                    return {
                        'passed': True,
                        'stdout': 'No specific tests run',
                        'stderr': '',
                        'returncode': 0
                    }
                    
        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'stdout': '',
                'stderr': 'Tests timed out after 5 minutes',
                'returncode': 124  # Standard timeout exit code
            }
        except Exception as e:
            return {
                'passed': False,
                'stdout': '',
                'stderr': f'Test execution failed: {str(e)}',
                'returncode': 1
            }
    
    def apply_patch_and_test(self, original_file_path, patched_content, test_command=None):
        """
        Apply a patch to a file and run tests
        
        :param original_file_path: Path to the original file
        :param patched_content: New content to write to the file
        :param test_command: Custom test command to run
        :return: dict with test results and whether patch is acceptable
        """
        # Create a temporary copy of the workspace
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_workspace = Path(temp_dir) / "workspace"
            shutil.copytree(self.workspace_path, temp_workspace)
            
            # Apply the patch to the temporary file
            temp_file_path = temp_workspace / original_file_path
            try:
                temp_file_path.parent.mkdir(parents=True, exist_ok=True)
                temp_file_path.write_text(patched_content)
                print(f"📝 Đã áp dụng bản vá vào {temp_file_path}")
            except Exception as e:
                return {
                    'passed': False,
                    'stdout': '',
                    'stderr': f'Failed to apply patch: {str(e)}',
                    'returncode': 1,
                    'patch_accepted': False
                }
            
            # Run tests on the patched file
            test_result = self.run_tests(
                file_path=temp_file_path if temp_file_path.exists() else None,
                test_command=test_command
            )
            
            # Determine if patch is acceptable based on test results
            # For now, we'll accept if tests pass or if there are no tests
            patch_accepted = test_result['passed'] or (
                test_result['returncode'] == 0 and 
                not test_result['stdout'] and 
                not test_result['stderr']
            )
            
            test_result['patch_accepted'] = patch_accepted
            return test_result

# Example usage
if __name__ == "__main__":
    # This would typically be used by evo_autofix.py
    tester = PatchTester()
    
    # Example: test current state
    result = tester.run_tests()
    print(f"Test result: {'✅ Passed' if result['passed'] else '❌ Failed'}")
    if result['stderr']:
        print(f"Errors: {result['stderr']}")