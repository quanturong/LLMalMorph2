"""
Example: Automated Compilation & Testing Pipeline
"""
import subprocess
import os
import logging
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompilationStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CompilationResult:
    status: CompilationStatus
    output: str
    errors: List[str]
    warnings: List[str]
    executable_path: Optional[str] = None


@dataclass
class TestResult:
    passed: bool
    output: str
    failures: List[str]


class CompilationPipeline:
    """Automated compilation and testing pipeline"""
    
    def __init__(self, compiler: str = "gcc", timeout: int = 30):
        self.compiler = compiler
        self.timeout = timeout
    
    def compile(
        self,
        source_file: str,
        output_file: Optional[str] = None,
        flags: List[str] = None,
    ) -> CompilationResult:
        """
        Compile source file and return result.
        
        Args:
            source_file: Path to source file
            output_file: Optional output executable path
            flags: Compiler flags
        
        Returns:
            CompilationResult
        """
        if output_file is None:
            output_file = os.path.splitext(source_file)[0]
        
        if flags is None:
            flags = ["-Wall", "-Wextra", "-std=c11"]
        
        cmd = [self.compiler] + flags + ["-o", output_file, source_file]
        
        logger.info(f"Compiling {source_file}...")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Compilation successful: {output_file}")
                return CompilationResult(
                    status=CompilationStatus.SUCCESS,
                    output=result.stdout,
                    errors=[],
                    warnings=self._extract_warnings(result.stderr),
                    executable_path=output_file,
                )
            else:
                logger.error(f"✗ Compilation failed")
                errors = self._extract_errors(result.stderr)
                return CompilationResult(
                    status=CompilationStatus.FAILED,
                    output=result.stdout,
                    errors=errors,
                    warnings=self._extract_warnings(result.stderr),
                )
        
        except subprocess.TimeoutExpired:
            logger.error(f"✗ Compilation timeout")
            return CompilationResult(
                status=CompilationStatus.TIMEOUT,
                output="",
                errors=["Compilation timeout"],
                warnings=[],
            )
        except Exception as e:
            logger.error(f"✗ Compilation error: {e}")
            return CompilationResult(
                status=CompilationStatus.FAILED,
                output="",
                errors=[str(e)],
                warnings=[],
            )
    
    def test(
        self,
        executable: str,
        test_cases: List[Dict] = None,
    ) -> TestResult:
        """
        Run tests on executable.
        
        Args:
            executable: Path to executable
            test_cases: List of test cases
        
        Returns:
            TestResult
        """
        if not os.path.exists(executable):
            return TestResult(
                passed=False,
                output="",
                failures=["Executable not found"],
            )
        
        if test_cases is None:
            # Basic smoke test - just run executable
            try:
                result = subprocess.run(
                    [executable],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return TestResult(
                    passed=result.returncode == 0,
                    output=result.stdout,
                    failures=[] if result.returncode == 0 else ["Non-zero exit code"],
                )
            except Exception as e:
                return TestResult(
                    passed=False,
                    output="",
                    failures=[str(e)],
                )
        
        # Run test cases
        failures = []
        for test_case in test_cases:
            try:
                result = subprocess.run(
                    [executable] + test_case.get("args", []),
                    input=test_case.get("input", ""),
                    capture_output=True,
                    text=True,
                    timeout=test_case.get("timeout", 5),
                )
                
                expected_output = test_case.get("expected_output")
                if expected_output and result.stdout.strip() != expected_output.strip():
                    failures.append(f"Test case failed: {test_case.get('name', 'unknown')}")
            except Exception as e:
                failures.append(f"Test case error: {e}")
        
        return TestResult(
            passed=len(failures) == 0,
            output="",
            failures=failures,
        )
    
    def _extract_errors(self, stderr: str) -> List[str]:
        """Extract error messages from compiler output"""
        errors = []
        for line in stderr.split('\n'):
            if 'error:' in line.lower():
                errors.append(line.strip())
        return errors
    
    def _extract_warnings(self, stderr: str) -> List[str]:
        """Extract warning messages from compiler output"""
        warnings = []
        for line in stderr.split('\n'):
            if 'warning:' in line.lower():
                warnings.append(line.strip())
        return warnings


class AutoFixer:
    """Automatically fix compilation errors using LLM"""
    
    def __init__(self, llm_provider):
        self.llm = llm_provider
    
    def fix_errors(
        self,
        source_code: str,
        errors: List[str],
        language: str = "c",
    ) -> str:
        """
        Fix compilation errors using LLM.
        
        Args:
            source_code: Original source code
            errors: List of error messages
            language: Programming language
        
        Returns:
            Fixed source code
        """
        error_text = "\n".join(errors)
        
        prompt = f"""
The following {language} code has compilation errors:

```{language}
{source_code}
```

Errors:
{error_text}

Please fix the compilation errors while maintaining the same functionality.
Return only the fixed code without explanations.
"""
        
        try:
            fixed_code = self.llm.generate(
                system_prompt="You are a code fixing assistant.",
                user_prompt=prompt,
            )
            
            # Extract code from response
            import re
            code_blocks = re.findall(r'```(?:python|c|cpp)?\n(.*?)```', fixed_code, re.DOTALL)
            if code_blocks:
                return code_blocks[0]
            return fixed_code
        
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
            return source_code


def example_automated_pipeline():
    """Example: Automated compilation pipeline"""
    print("=" * 60)
    print("Automated Compilation Pipeline Example")
    print("=" * 60)
    
    # Create pipeline
    pipeline = CompilationPipeline(compiler="gcc")
    
    # Example source file
    source_code = """
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    printf("Sum: %d\\n", add(2, 3));
    return 0;
}
"""
    
    # Write to temp file
    temp_file = "temp_example.c"
    with open(temp_file, "w") as f:
        f.write(source_code)
    
    try:
        # Compile
        result = pipeline.compile(temp_file, "temp_example")
        
        if result.status == CompilationStatus.SUCCESS:
            print(f"✓ Compilation successful")
            print(f"  Executable: {result.executable_path}")
            print(f"  Warnings: {len(result.warnings)}")
            
            # Test
            test_result = pipeline.test(result.executable_path)
            if test_result.passed:
                print(f"✓ Tests passed")
            else:
                print(f"✗ Tests failed: {test_result.failures}")
        else:
            print(f"✗ Compilation failed")
            print(f"  Errors: {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3
                print(f"    - {error}")
            
            # Auto-fix example (would need LLM provider)
            # fixer = AutoFixer(llm_provider)
            # fixed_code = fixer.fix_errors(source_code, result.errors)
    
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists("temp_example"):
            os.remove("temp_example")


if __name__ == "__main__":
    example_automated_pipeline()

