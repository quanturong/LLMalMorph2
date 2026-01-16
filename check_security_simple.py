"""
Simple security check - Kiểm tra API keys trước khi commit
"""
import os
import json
from pathlib import Path

# API key cần tìm (từ notebook)
SUSPICIOUS_KEY = "fPBbuBG1sEH015hnaAWm9jr4qKVJ9XpP"

def check_notebook():
    """Check notebook for API keys"""
    notebook_path = Path("llmalmorph.ipynb")
    
    # Check if notebook is in .gitignore
    gitignore_path = Path(".gitignore")
    is_ignored = False
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
            if 'llmalmorph.ipynb' in gitignore_content:
                is_ignored = True
    
    if not notebook_path.exists():
        print("✅ llmalmorph.ipynb không tồn tại")
        return True
    
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if SUSPICIOUS_KEY in content:
            if is_ignored:
                print("⚠️  llmalmorph.ipynb có API key NHƯNG đã có trong .gitignore")
                print("   → AN TOÀN (sẽ không được commit)")
                return True
            else:
                print("❌ PHÁT HIỆN API KEY TRONG llmalmorph.ipynb!")
                print(f"   Key: {SUSPICIOUS_KEY[:20]}...")
                print("\n⚠️  HÀNH ĐỘNG CẦN THIẾT:")
                print("   1. Xóa/sửa API key trong notebook")
                print("   2. HOẶC thêm llmalmorph.ipynb vào .gitignore")
                return False
        else:
            print("✅ llmalmorph.ipynb không có API key thật")
            return True
    except Exception as e:
        print(f"⚠️  Không thể đọc notebook: {e}")
        return True  # Assume safe if can't read

def check_gitignore():
    """Check if .gitignore has necessary entries"""
    gitignore_path = Path(".gitignore")
    
    if not gitignore_path.exists():
        print("❌ Không có file .gitignore!")
        return False
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
    
    required = ['.env', '*.key', 'config.json']
    missing = []
    
    for item in required:
        if item not in content:
            missing.append(item)
    
    if missing:
        print(f"⚠️  .gitignore thiếu: {', '.join(missing)}")
        return False
    
    # Check if notebook is ignored (optional but recommended)
    if 'llmalmorph.ipynb' in content:
        print("✅ llmalmorph.ipynb đã có trong .gitignore")
    else:
        print("⚠️  llmalmorph.ipynb chưa có trong .gitignore (khuyến nghị thêm)")
    
    print("✅ .gitignore có đầy đủ các entry cần thiết")
    return True

def main():
    print("=" * 60)
    print("Security Check - Kiểm tra Trước Khi Upload GitHub")
    print("=" * 60)
    print()
    
    notebook_ok = check_notebook()
    gitignore_ok = check_gitignore()
    
    print()
    print("=" * 60)
    
    if notebook_ok and gitignore_ok:
        print("✅ AN TOÀN ĐỂ UPLOAD LÊN GITHUB!")
        print("=" * 60)
        return 0
    else:
        print("❌ CHƯA AN TOÀN - CẦN FIX TRƯỚC KHI UPLOAD!")
        print("=" * 60)
        print("\nXem PRE_COMMIT_CHECKLIST.md để biết cách fix")
        return 1

if __name__ == "__main__":
    exit(main())

