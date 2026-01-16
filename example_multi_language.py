"""
Example: Using multi-language support in LLMalMorph
"""
import os
import logging
from src.languages import get_language, get_supported_languages
from src.config import get_config, setup_logging

# Setup logging
config = get_config()
setup_logging(config)
logger = logging.getLogger(__name__)


def example_language_detection():
    """Example: Automatic language detection"""
    print("=" * 60)
    print("Example 1: Language Detection")
    print("=" * 60)
    
    test_files = [
        "example.c",
        "example.cpp",
        "example.py",
        "example.js",
    ]
    
    for file_path in test_files:
        # Create dummy content for testing
        if file_path.endswith('.c'):
            content = "#include <stdio.h>\nint main() { return 0; }"
        elif file_path.endswith('.cpp'):
            content = "#include <iostream>\nint main() { return 0; }"
        elif file_path.endswith('.py'):
            content = "def main():\n    pass"
        else:
            content = "function main() {}"
        
        lang = get_language(file_path, content)
        if lang:
            print(f"✓ {file_path}: Detected as {lang.name}")
        else:
            print(f"✗ {file_path}: Not supported")


def example_parse_python():
    """Example: Parsing Python code"""
    print("\n" + "=" * 60)
    print("Example 2: Parsing Python Code")
    print("=" * 60)
    
    python_code = """
import os
import sys

def add(a, b):
    return a + b

class Calculator:
    def __init__(self):
        self.value = 0
    
    def calculate(self, x, y):
        return x * y
"""
    
    lang = get_language("example.py", python_code)
    if lang:
        try:
            structure = lang.parse("example.py", python_code)
            print(f"✓ Parsed {len(structure.functions)} functions")
            print(f"✓ Parsed {len(structure.classes)} classes")
            print(f"✓ Found {len(structure.headers)} imports")
            
            for func in structure.functions:
                print(f"  - Function: {func.name}")
        except Exception as e:
            print(f"✗ Parse error: {e}")
    else:
        print("✗ Python language not available")


def example_language_specific_prompts():
    """Example: Language-specific prompts"""
    print("\n" + "=" * 60)
    print("Example 3: Language-Specific Prompts")
    print("=" * 60)
    
    languages = ['c', 'cpp', 'python']
    
    for lang_name in languages:
        lang = get_language(f"example.{lang_name}")
        if lang:
            system_prompt = lang.get_system_prompt()
            mutation_prompt = lang.get_mutation_prompt(
                num_functions=1,
                function_names=["test_function"],
            )
            
            print(f"\n{lang.name.upper()} Language:")
            print(f"System Prompt (first 100 chars): {system_prompt[:100]}...")
            print(f"Mutation Prompt (first 100 chars): {mutation_prompt[:100]}...")


def example_supported_languages():
    """Example: List supported languages"""
    print("\n" + "=" * 60)
    print("Example 4: Supported Languages")
    print("=" * 60)
    
    supported = get_supported_languages()
    print(f"Supported file extensions: {', '.join(supported)}")
    
    # Group by language
    lang_map = {}
    for ext in supported:
        lang = get_language(f"test{ext}")
        if lang:
            lang_name = lang.name
            if lang_name not in lang_map:
                lang_map[lang_name] = []
            lang_map[lang_name].append(ext)
    
    print("\nLanguages by extension:")
    for lang_name, exts in lang_map.items():
        print(f"  {lang_name}: {', '.join(exts)}")


if __name__ == "__main__":
    print("Multi-Language Support Examples\n")
    
    try:
        example_supported_languages()
        example_language_detection()
        example_parse_python()
        example_language_specific_prompts()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed")
        print("=" * 60)
        
    except Exception as e:
        logger.exception("Error running examples")
        print(f"\n✗ Error: {e}")

