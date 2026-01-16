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
            f"You are an expert {language} programmer specializing in fixing compilation errors. "
            "Your task is to fix ALL compilation errors to make the code compile successfully.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. For missing header files (e.g., 'No such file or directory', 'fatal error'):\n"
            "   - If the header is NOT used in the code: REMOVE the #include line completely\n"
            "   - If the header IS used: Comment out the #include and add minimal stub declarations\n"
            "   - Example: If 'dokani.h' is missing, comment out '#include <dokani.h>' and add:\n"
            "     // #include <dokani.h>  // Missing header - commented out\n"
            "     // Minimal stubs if needed\n\n"
            "2. For undefined types/functions:\n"
            "   - Add forward declarations or minimal implementations\n"
            "   - Use void* for unknown types if needed\n\n"
            "3. For syntax errors:\n"
            "   - Fix all syntax issues completely\n"
            "   - Ensure all brackets, parentheses, and semicolons are correct\n\n"
            "4. IMPORTANT: The code MUST compile successfully after your fix.\n"
            "   Return ONLY the complete fixed code, nothing else."
        )
        
        # Analyze errors to provide better context
        missing_headers = [e for e in errors if 'no such file' in e.lower() or 'fatal error' in e.lower()]
        syntax_errors = [e for e in errors if 'error:' in e.lower() and 'no such file' not in e.lower()]
        
        error_context = ""
        if missing_headers:
            error_context += "\nMISSING HEADERS DETECTED:\n"
            for err in missing_headers[:5]:  # Limit to first 5
                error_context += f"  - {err}\n"
            error_context += "\nACTION REQUIRED: Comment out or remove these #include statements.\n\n"
        
        if syntax_errors:
            error_context += "SYNTAX ERRORS:\n"
            for err in syntax_errors[:5]:  # Limit to first 5
                error_context += f"  - {err}\n"
            error_context += "\nACTION REQUIRED: Fix all syntax errors.\n\n"
        
        user_prompt = f"""
The following {language} code has compilation errors that prevent it from compiling:

```{language}
{source_code}
```

COMPILATION ERRORS:
{error_text}

{error_context}
YOUR TASK:
1. Fix ALL compilation errors to make the code compile successfully
2. For missing headers: Comment them out or remove them, add stubs only if absolutely necessary
3. For syntax errors: Fix them completely
4. Maintain the core functionality of the code
5. Return ONLY the complete fixed code within code blocks (```{language} ... ```)
6. Do NOT include any explanations, comments, or text outside the code blocks

The fixed code MUST compile without errors.
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

