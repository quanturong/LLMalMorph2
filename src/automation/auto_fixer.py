"""
Automatic error fixing using LLM.
Fixes compilation errors and code issues automatically.
"""
import logging
import re
from typing import List, Optional, Tuple
from llm_api import get_llm_provider, LLMAPIError
try:
    from .error_analyzer import ErrorAnalyzer, ErrorType
except ImportError:
    # Fallback if error_analyzer is not available
    ErrorAnalyzer = None
    ErrorType = None

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
        use_pattern_fixes: bool = True,
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
        
        # Analyze errors to get better context
        if ErrorAnalyzer:
            try:
                error_infos = ErrorAnalyzer.classify_errors(errors)
                strategy = ErrorAnalyzer.get_fix_strategy(error_infos)
                # Build context-aware system prompt
                system_prompt = self._build_system_prompt(language, strategy)
                # Build detailed error context
                error_context = self._build_error_context(error_infos, strategy)
            except Exception as e:
                logger.warning(f"Error analysis failed, using fallback: {e}")
                system_prompt = self._build_fallback_system_prompt(language)
                error_context = self._build_fallback_error_context(errors)
        else:
            system_prompt = self._build_fallback_system_prompt(language)
            error_context = self._build_fallback_error_context(errors)
        
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
                        # Re-analyze errors for next attempt (will be updated by caller with new errors)
                        user_prompt = f"""
The following {language} code still has compilation errors after previous fix attempt:

```{language}
{fixed_code}
```

Previous Errors:
{error_text}

{error_context}

Please fix the REMAINING compilation errors. Be more aggressive:
1. Comment out problematic code sections if they can't be fixed
2. Add minimal stub implementations for missing functions
3. Remove or comment out unused includes and code
4. Ensure the code compiles successfully

Return only the fixed code within code blocks (```{language} ... ```).
"""
                    
                    # Return fixed code - verification will be done by compilation step
                    # If this is the last attempt, return what we have
                    if attempt == max_attempts - 1:
                        # Ensure we return a valid string
                        if fixed_code and isinstance(fixed_code, str):
                            return fixed_code, True, []
                        else:
                            return source_code, False, errors
                    # Otherwise, continue to next attempt if compilation still fails
                    # (This will be handled by the caller)
                    # Ensure we return a valid string
                    if fixed_code and isinstance(fixed_code, str):
                        return fixed_code, True, []
                    else:
                        return source_code, False, errors
                else:
                    logger.warning(f"No code extracted from response (attempt {attempt + 1})")
                    # If no code extracted and this is the last attempt, return original code
                    if attempt == max_attempts - 1:
                        return source_code, False, errors
            
            except LLMAPIError as e:
                logger.error(f"LLM API error: {e}")
                break
            
            except Exception as e:
                logger.error(f"Unexpected error during auto-fix: {e}")
                break
        
        logger.warning("Failed to fix errors after all attempts")
        # Ensure we always return a valid string
        if fixed_code and isinstance(fixed_code, str):
            return fixed_code, False, remaining_errors
        return source_code, False, remaining_errors
    
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
    
    def _build_fallback_system_prompt(self, language: str) -> str:
        """Fallback system prompt when error analyzer is not available"""
        return (
            f"You are an expert {language} programmer specializing in fixing compilation errors. "
            "Your task is to fix ALL compilation errors to make the code compile successfully.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. For missing header files: Comment them out or remove them, add minimal stubs if needed\n"
            "2. For undefined symbols: Add forward declarations or minimal implementations\n"
            "3. For syntax errors: Fix all syntax issues completely\n"
            "4. IMPORTANT: The code MUST compile successfully after your fix.\n"
            "   Return ONLY the complete fixed code, nothing else."
        )
    
    def _build_fallback_error_context(self, errors: List[str]) -> str:
        """Fallback error context when error analyzer is not available"""
        missing_headers = [e for e in errors if 'no such file' in e.lower() or 'fatal error' in e.lower()]
        syntax_errors = [e for e in errors if 'error:' in e.lower() and 'no such file' not in e.lower()]
        
        context = ""
        if missing_headers:
            context += "\n⚠️ MISSING HEADERS DETECTED:\n"
            for err in missing_headers[:5]:
                context += f"    - {err}\n"
            context += "\n  ACTION: Comment out #include statements and add minimal stubs.\n\n"
        
        if syntax_errors:
            context += "\n⚠️ SYNTAX ERRORS DETECTED:\n"
            for err in syntax_errors[:5]:
                context += f"    - {err}\n"
            context += "\n  ACTION: Fix all syntax issues completely.\n\n"
        
        return context
    
    def _build_system_prompt(self, language: str, strategy: dict) -> str:
        """Build system prompt based on error analysis strategy"""
        prompt = (
            f"You are an expert {language} programmer specializing in fixing compilation errors. "
            "Your task is to fix ALL compilation errors to make the code compile successfully.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
        )
        
        if strategy.get('has_missing_headers'):
            prompt += (
                "1. For missing header files (e.g., 'No such file or directory', 'fatal error'):\n"
                "   - If the header is NOT used in the code: REMOVE the #include line completely\n"
                "   - If the header IS used: Comment out the #include and add minimal stub declarations\n"
                "   - For each missing header, add forward declarations for types/functions used\n"
                "   - Example: If 'dokani.h' is missing, comment out '#include <dokani.h>' and add:\n"
                "     // #include <dokani.h>  // Missing header - commented out\n"
                "     // Forward declarations for types/functions from dokani.h\n\n"
            )
        
        if strategy.get('has_undefined_symbols'):
            prompt += (
                "2. For undefined symbols (functions, variables, types):\n"
                "   - Add forward declarations at the top of the file\n"
                "   - For functions: Add minimal stub implementations if needed\n"
                "   - For types: Use void* or add minimal struct definitions\n"
                "   - For variables: Add extern declarations or remove if unused\n\n"
            )
        
        if strategy.get('has_syntax_errors'):
            prompt += (
                "3. For syntax errors:\n"
                "   - Fix all syntax issues completely (missing semicolons, brackets, etc.)\n"
                "   - Ensure all brackets, parentheses, and semicolons are correct\n"
                "   - Check for typos in keywords and identifiers\n\n"
            )
        
        if strategy.get('has_type_mismatches'):
            prompt += (
                "4. For type mismatches:\n"
                "   - Add explicit type casts where needed\n"
                "   - Fix function signatures to match declarations\n"
                "   - Ensure return types match function definitions\n\n"
            )
        
        prompt += (
            "5. IMPORTANT: The code MUST compile successfully after your fix.\n"
            "   - Be aggressive: Comment out problematic code if necessary\n"
            "   - Add minimal stubs to make code compile\n"
            "   - Return ONLY the complete fixed code, nothing else.\n"
        )
        
        return prompt
    
    def _build_error_context(self, error_infos: List, strategy: dict) -> str:
        """Build detailed error context for LLM"""
        context = ""
        
        if strategy.get('has_missing_headers'):
            context += "\n⚠️ MISSING HEADERS DETECTED:\n"
            missing_headers = strategy.get('missing_headers', [])
            if missing_headers:
                context += "  Headers to fix:\n"
                for header in missing_headers[:10]:  # Limit to first 10
                    context += f"    - {header}\n"
            else:
                # Fallback to showing error messages
                header_errors = [e.error_text for e in error_infos if e.error_type == ErrorType.MISSING_HEADER]
                for err in header_errors[:5]:
                    context += f"    - {err}\n"
            context += "\n  ACTION: Comment out #include statements and add minimal stubs.\n\n"
        
        if strategy.get('has_undefined_symbols'):
            context += "\n⚠️ UNDEFINED SYMBOLS DETECTED:\n"
            undefined_symbols = strategy.get('undefined_symbols', [])
            if undefined_symbols:
                context += "  Symbols to fix:\n"
                for symbol in undefined_symbols[:10]:  # Limit to first 10
                    context += f"    - {symbol}\n"
            else:
                symbol_errors = [e.error_text for e in error_infos if e.error_type == ErrorType.UNDEFINED_SYMBOL]
                for err in symbol_errors[:5]:
                    context += f"    - {err}\n"
            context += "\n  ACTION: Add forward declarations or stub implementations.\n\n"
        
        if strategy.get('has_syntax_errors'):
            context += "\n⚠️ SYNTAX ERRORS DETECTED:\n"
            syntax_errors = [e.error_text for e in error_infos if e.error_type == ErrorType.SYNTAX_ERROR]
            for err in syntax_errors[:5]:
                context += f"    - {err}\n"
            context += "\n  ACTION: Fix all syntax issues completely.\n\n"
        
        # Show error type summary
        if strategy.get('error_types'):
            context += "\n📊 ERROR SUMMARY:\n"
            for error_type, count in strategy['error_types'].items():
                context += f"  - {error_type}: {count} error(s)\n"
            context += "\n"
        
        return context

