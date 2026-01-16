"""
Security check script - Kiểm tra API keys và sensitive data trước khi commit
"""
import os
import re
from pathlib import Path

# Patterns to check for
SENSITIVE_PATTERNS = [
    r'["\']?[A-Za-z0-9]{32,}["\']?\s*=\s*["\']?[A-Za-z0-9]{32,}["\']?',  # Long alphanumeric strings (potential API keys)
    r'API[_\s]*KEY\s*=\s*["\'][^"\']+["\']',  # API_KEY = "..."
    r'api[_\s]*key\s*=\s*["\'][^"\']+["\']',  # api_key = "..."
    r'MISTRAL_API_KEY\s*=\s*["\'][^"\']+["\']',  # MISTRAL_API_KEY = "..."
    r'password\s*=\s*["\'][^"\']+["\']',  # password = "..."
    r'secret\s*=\s*["\'][^"\']+["\']',  # secret = "..."
    r'token\s*=\s*["\'][^"\']+["\']',  # token = "..."
]

# Known safe patterns (example keys, placeholders)
SAFE_PATTERNS = [
    r'your-.*-key-here',
    r'your-.*-here',
    r'example',
    r'placeholder',
    r'xxx',
    r'xxxx',
    r'os\.getenv',
    r'os\.environ\.get',
    r'environment variable',
]

# Files to check
FILES_TO_CHECK = [
    '*.py',
    '*.ipynb',
    '*.md',
    '*.json',
    '*.yaml',
    '*.yml',
    '*.cfg',
    '*.ini',
]

# Files/directories to skip
SKIP_PATTERNS = [
    '.git',
    '__pycache__',
    '.venv',
    'venv',
    'env',
    'node_modules',
    '.ipynb_checkpoints',
    'build',
    'dist',
    '.env',
    '.env.example',
]


def is_safe_line(line: str) -> bool:
    """Check if line contains safe patterns (not real keys)"""
    line_lower = line.lower()
    for pattern in SAFE_PATTERNS:
        if re.search(pattern, line_lower):
            return True
    return False


def check_file(file_path: Path) -> list:
    """Check a single file for sensitive data"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Skip comments and safe patterns
                if is_safe_line(line):
                    continue
                
                # Check each pattern
                for pattern in SENSITIVE_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                        })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return issues


def should_skip(path: Path) -> bool:
    """Check if path should be skipped"""
    path_str = str(path)
    for skip_pattern in SKIP_PATTERNS:
        if skip_pattern in path_str:
            return True
    return False


def main():
    """Main security check"""
    print("=" * 60)
    print("Security Check - Kiểm tra API Keys và Sensitive Data")
    print("=" * 60)
    print()
    
    root = Path('.')
    all_issues = []
    
    # Check Python files
    for pattern in ['*.py', '*.ipynb', '*.md', '*.json']:
        for file_path in root.rglob(pattern):
            if should_skip(file_path):
                continue
            
            if file_path.is_file():
                issues = check_file(file_path)
                all_issues.extend(issues)
    
    # Report results
    if all_issues:
        print("⚠️  PHÁT HIỆN CÁC VẤN ĐỀ BẢO MẬT:")
        print("=" * 60)
        
        for issue in all_issues:
            print(f"\n📁 File: {issue['file']}")
            print(f"   Line {issue['line']}: {issue['content'][:80]}")
            print(f"   Pattern: {issue['pattern']}")
        
        print("\n" + "=" * 60)
        print("❌ KHÔNG AN TOÀN ĐỂ UPLOAD!")
        print("=" * 60)
        print("\nHãy:")
        print("1. Xóa/sửa các API keys trong các file trên")
        print("2. Sử dụng environment variables thay vì hardcode")
        print("3. Thêm các file chứa keys vào .gitignore")
        print("4. Chạy lại script này để verify")
        return 1
    else:
        print("✅ KHÔNG PHÁT HIỆN VẤN ĐỀ BẢO MẬT")
        print("=" * 60)
        print("\nHệ thống an toàn để upload lên GitHub!")
        print("\nLưu ý:")
        print("- Đảm bảo .env file đã có trong .gitignore")
        print("- Đảm bảo không có API keys trong code")
        print("- Sử dụng environment variables")
        return 0


if __name__ == "__main__":
    exit(main())

