"""
Automatic error fixing using LLM.
Fixes compilation errors and code issues automatically.
"""
import logging
import re
from typing import List, Optional, Tuple
from llm_api import get_llm_provider, LLMAPIError

logger = logging.getLogger(__name__)


class AutoFixer:
    """
    Automatically fix compilation errors and code issues using LLM.
    """
    
    def __init__(self, llm_model: str = "codestral-2508", api_key: Optional[str] = None):
        """
        Initialize auto-fixer.
        
        Args:
            llm_model: LLM model to use
            api_key: Optional API key for Mistral
        """
        self.llm_model = llm_model
        self.api_key = api_key
        self.llm_provider = None
        
        try:
            self.llm_provider = get_llm_provider(llm_model, api_key=api_key)
            logger.info(f"Auto-fixer initialized with model: {llm_model}")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM provider: {e}")
    
    def fix_compilation_errors(
        self,
        source_code: str,
        errors: List[str],
        language: str = "c",
        max_attempts: int = 3,
    ) -> Tuple[str, bool, List[str]]:
        """
        Fix compilation errors using LLM.
        
        Args:
            source_code: Original source code
            errors: List of compilation error messages
            language: Programming language
            max_attempts: Maximum number of fix attempts
        
        Returns:
            Tuple of (fixed_code, success, remaining_errors)
        """
        if not self.llm_provider:
            logger.error("LLM provider not available")
            return source_code, False, errors
        
        if not errors:
            return source_code, True, []
        
        error_text = "\n".join([f"  - {error}" for error in errors])
        
        system_prompt = (
            f"You are an expert {language} programmer. "
            "Your task is to fix compilation errors in code while maintaining "
            "the exact same functionality. Return only the fixed code without explanations.\n\n"
            "For missing header files (e.g., 'No such file or directory'), you can either:\n"
            "1. Comment out the problematic #include if it's not essential\n"
            "2. Add minimal stub declarations if the header is needed\n"
            "3. Remove the include if it's not used in the code\n"
            "Prioritize making the code compile while preserving functionality."
        )
        
        user_prompt = f"""
The following {language} code has compilation errors:

```{language}
{source_code}
```

Compilation Errors:
{error_text}

Please fix these compilation errors while maintaining the same functionality.
For missing header files, comment them out or add minimal stubs if needed.
Return only the fixed code within code blocks (```{language} ... ```).
Do not include any explanations or comments outside the code blocks.
"""
        
        fixed_code = source_code
        remaining_errors = errors.copy()
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempting to fix errors (attempt {attempt + 1}/{max_attempts})...")
                
                response = self.llm_provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=self.llm_model.replace(":", "-"),
                )
                
                # Extract code from response
                extracted_code = self._extract_code_from_response(response, language)
                
                if extracted_code:
                    fixed_code = extracted_code
                    logger.info(f"✓ Generated fix (attempt {attempt + 1})")
                    
                    # Update user_prompt for next attempt with fixed code if needed
                    if attempt < max_attempts - 1:
                        user_prompt = f"""
The following {language} code still has compilation errors after previous fix attempt:

```{language}
{fixed_code}
```

Previous Errors:
{error_text}

Please fix the remaining compilation errors. Make sure to:
1. Comment out or remove missing header includes
2. Add minimal stub declarations if needed
3. Fix any syntax errors
4. Ensure the code compiles successfully

Return only the fixed code within code blocks (```{language} ... ```).
"""
                    
                    # Return fixed code - verification will be done by compilation step
                    # If this is the last attempt, return what we have
                    if attempt == max_attempts - 1:
                        return fixed_code, True, []
                    # Otherwise, continue to next attempt if compilation still fails
                    # (This will be handled by the caller)
                    return fixed_code, True, []
                else:
                    logger.warning(f"No code extracted from response (attempt {attempt + 1})")
            
            except LLMAPIError as e:
                logger.error(f"LLM API error: {e}")
                break
            
            except Exception as e:
                logger.error(f"Unexpected error during auto-fix: {e}")
                break
        
        logger.warning("Failed to fix errors after all attempts")
        return fixed_code, False, remaining_errors
    
    def fix_code_issues(
        self,
        source_code: str,
        issues: List[str],
        language: str = "c",
    ) -> Tuple[str, bool]:
        """
        Fix code quality issues (warnings, style, etc.).
        
        Args:
            source_code: Original source code
            issues: List of code issues
            language: Programming language
        
        Returns:
            Tuple of (fixed_code, success)
        """
        if not self.llm_provider:
            return source_code, False
        
        if not issues:
            return source_code, True
        
        issues_text = "\n".join([f"  - {issue}" for issue in issues])
        
        system_prompt = (
            f"You are an expert {language} programmer. "
            "Fix code quality issues while maintaining functionality."
        )
        
        user_prompt = f"""
The following {language} code has quality issues:

```{language}
{source_code}
```

Issues:
{issues_text}

Please fix these issues. Return only the fixed code within code blocks.
"""
        
        try:
            response = self.llm_provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.llm_model.replace(":", "-"),
            )
            
            fixed_code = self._extract_code_from_response(response, language)
            
            if fixed_code:
                return fixed_code, True
            
            return source_code, False
        
        except Exception as e:
            logger.error(f"Error fixing code issues: {e}")
            return source_code, False
    
    def _extract_code_from_response(self, response: str, language: str) -> Optional[str]:
        """
        Extract code from LLM response.
        
        Args:
            response: LLM response text
            language: Programming language
        
        Returns:
            Extracted code or None
        """
        # Try to find code blocks
        patterns = [
            rf'```{language}\s*\n(.*?)```',
            rf'```\s*\n(.*?)```',
            rf'```{language}(.*?)```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                code = matches[0].strip()
                if code:
                    return code
        
        # If no code blocks, try to extract if response looks like code
        lines = response.strip().split('\n')
        if len(lines) > 5:  # Likely code if many lines
            # Check if it looks like code (has brackets, semicolons, etc.)
            code_indicators = ['{', '}', ';', '(', ')', '#include', 'def ', 'class ']
            if any(indicator in response for indicator in code_indicators):
                return response.strip()
        
        return None

