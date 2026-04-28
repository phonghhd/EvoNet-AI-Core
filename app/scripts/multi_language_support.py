import os
import re
from typing import Dict, List, Optional
from pathlib import Path

class MultiLanguageSupport:
    """Multi-language support for code analysis and patching"""
    
    # Supported languages and their file extensions
    SUPPORTED_LANGUAGES = {
        'python': ['.py'],
        'javascript': ['.js', '.jsx'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'c': ['.c', '.h'],
        'cpp': ['.cpp', '.hpp', '.h'],
        'csharp': ['.cs'],
        'go': ['.go'],
        'rust': ['.rs'],
        'php': ['.php'],
        'ruby': ['.rb'],
        'swift': ['.swift'],
        'kotlin': ['.kt'],
    }
    
    # Language-specific patterns for code analysis
    LANGUAGE_PATTERNS = {
        'python': {
            'comment': r'#.*',
            'string': r'(["\'])(?:(?=(\\?))\2.)*?\1',
            'function_def': r'def\s+(\w+)\s*\([^)]*\):',
            'class_def': r'class\s+(\w+)',
            'import': r'(import\s+[\w\.]+|from\s+[\w\.]+\s+import\s+[\w\., ]+)'
        },
        'javascript': {
            'comment': r'//.*|/\*.*?\*/',
            'string': r'(["\'])(?:(?=(\\?))\2.)*?\1',
            'function_def': r'(function\s+(\w+)|(\w+)\s*=>)',
            'class_def': r'class\s+(\w+)',
            'import': r'(import\s+.*?from\s+["\'][\w\.\/]+["\']|require\(.+?\))'
        },
        'java': {
            'comment': r'//.*|/\*.*?\*/',
            'string': r'(["\'])(?:(?=(\\?))\2.)*?\1',
            'function_def': r'(public|private|protected).*?\s+(\w+)\s*\([^)]*\)\s*{',
            'class_def': r'class\s+(\w+)',
            'import': r'import\s+[\w\.]+;'
        }
    }
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language based on file extension"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        for language, extensions in self.SUPPORTED_LANGUAGES.items():
            if suffix in extensions:
                return language
        
        return None
    
    def get_language_patterns(self, language: str) -> Dict[str, str]:
        """Get language-specific patterns for code analysis"""
        return self.LANGUAGE_PATTERNS.get(language, {})
    
    def extract_functions(self, code: str, language: str) -> List[str]:
        """Extract function definitions from code"""
        patterns = self.get_language_patterns(language)
        if 'function_def' not in patterns:
            return []
        
        function_pattern = patterns['function_def']
        matches = re.findall(function_pattern, code, re.MULTILINE)
        
        # Extract function names from matches
        function_names = []
        for match in matches:
            if isinstance(match, tuple):
                # Find the non-empty group which contains the function name
                for group in match:
                    if isinstance(group, str) and group and not group.isspace():
                        # Clean up the function name
                        func_name = group.strip()
                        if func_name and not func_name.startswith(('(', '{', '[')):
                            function_names.append(func_name)
                            break
            else:
                function_names.append(match.strip())
        
        return function_names
    
    def extract_classes(self, code: str, language: str) -> List[str]:
        """Extract class definitions from code"""
        patterns = self.get_language_patterns(language)
        if 'class_def' not in patterns:
            return []
        
        class_pattern = patterns['class_def']
        matches = re.findall(class_pattern, code, re.MULTILINE)
        return [match.strip() for match in matches if match.strip()]
    
    def remove_comments(self, code: str, language: str) -> str:
        """Remove comments from code"""
        patterns = self.get_language_patterns(language)
        if 'comment' not in patterns:
            return code
        
        comment_pattern = patterns['comment']
        return re.sub(comment_pattern, '', code, flags=re.MULTILINE | re.DOTALL)
    
    def remove_strings(self, code: str, language: str) -> str:
        """Remove string literals from code"""
        patterns = self.get_language_patterns(language)
        if 'string' not in patterns:
            return code
        
        string_pattern = patterns['string']
        return re.sub(string_pattern, '""', code)
    
    def get_imports(self, code: str, language: str) -> List[str]:
        """Extract import statements from code"""
        patterns = self.get_language_patterns(language)
        if 'import' not in patterns:
            return []
        
        import_pattern = patterns['import']
        matches = re.findall(import_pattern, code, re.MULTILINE)
        return [match.strip() for match in matches if match.strip()]
    
    def analyze_code_structure(self, file_path: str) -> Dict[str, any]:
        """Analyze code structure for a given file"""
        language = self.detect_language(file_path)
        if not language:
            return {"error": f"Unsupported language for file: {file_path}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Remove comments and strings for cleaner analysis
            clean_code = self.remove_comments(code, language)
            clean_code = self.remove_strings(clean_code, language)
            
            return {
                "language": language,
                "functions": self.extract_functions(clean_code, language),
                "classes": self.extract_classes(clean_code, language),
                "imports": self.get_imports(code, language),
                "lines_of_code": len(code.split('\n'))
            }
        except Exception as e:
            return {"error": f"Error analyzing {file_path}: {str(e)}"}
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages"""
        return list(self.SUPPORTED_LANGUAGES.keys())
    
    def get_file_extensions(self, language: str) -> List[str]:
        """Get file extensions for a specific language"""
        return self.SUPPORTED_LANGUAGES.get(language, [])

# Example usage
if __name__ == "__main__":
    # Create multi-language support instance
    mls = MultiLanguageSupport()
    
    # Example: analyze a Python file
    print("Supported languages:", mls.get_supported_languages())
    print("File extensions for Python:", mls.get_file_extensions('python'))
    
    # Example function extraction
    python_code = '''
def hello_world():
    # This is a comment
    print("Hello, World!")
    
def add_numbers(a, b):
    """Add two numbers"""
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''
    
    functions = mls.extract_functions(python_code, 'python')
    classes = mls.extract_classes(python_code, 'python')
    imports = mls.get_imports('import os\nimport sys', 'python')
    
    print("Functions:", functions)
    print("Classes:", classes)
    print("Imports:", imports)