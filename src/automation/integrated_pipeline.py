"""
Integrated automation pipeline combining compilation, QA, and auto-fixing.
"""
import logging
import os
from typing import Optional, Dict, List
from .compilation_pipeline import CompilationPipeline, CompilationStatus
from .auto_fixer import AutoFixer
from .quality_assurance import QualityAssurance

logger = logging.getLogger(__name__)


class IntegratedPipeline:
    """
    Integrated pipeline that combines compilation, QA checks, and auto-fixing.
    """
    
    def __init__(
        self,
        language: str = "c",
        compiler: Optional[str] = None,
        llm_model: str = "codestral-2508",
        api_key: Optional[str] = None,
        max_fix_attempts: int = 3,
    ):
        """
        Initialize integrated pipeline.
        
        Args:
            language: Programming language
            compiler: Compiler name (auto-detect if None)
            llm_model: LLM model for auto-fixing
            api_key: Optional API key
            max_fix_attempts: Maximum auto-fix attempts
        """
        self.language = language
        self.compiler_pipeline = CompilationPipeline(language=language, compiler=compiler)
        self.auto_fixer = AutoFixer(llm_model=llm_model, api_key=api_key)
        self.qa = QualityAssurance(language=language)
        self.max_fix_attempts = max_fix_attempts
        
        logger.info(
            f"Initialized integrated pipeline: "
            f"language={language}, model={llm_model}"
        )
    
    def process_variant(
        self,
        source_file: str,
        variant_code: Optional[str] = None,
        original_code: Optional[str] = None,
        auto_fix: bool = True,
        run_tests: bool = True,
    ) -> Dict:
        """
        Process a code variant through the full pipeline.
        
        Args:
            source_file: Path to source file
            variant_code: Optional variant code (if None, uses source_file)
            original_code: Optional original code for comparison
            auto_fix: Whether to auto-fix errors
            run_tests: Whether to run tests
        
        Returns:
            Dictionary with processing results
        """
        results = {
            'source_file': source_file,
            'compilation': None,
            'quality': None,
            'tests': None,
            'fixed_code': None,
            'success': False,
        }
        
        # Read variant code if not provided
        if variant_code is None:
            with open(source_file, 'r') as f:
                variant_code = f.read()
        
        # Write variant to temp file for compilation
        import tempfile
        # Use compiler pipeline's working directory to ensure file is accessible
        working_dir = self.compiler_pipeline.working_dir
        os.makedirs(working_dir, exist_ok=True)
        
        # Create temp file in working directory
        file_ext = os.path.splitext(source_file)[1] or ('.c' if self.language == 'c' else '.cpp')
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=file_ext,
            delete=False,
            dir=working_dir
        )
        temp_file.write(variant_code)
        temp_file.flush()  # Ensure data is written to buffer
        os.fsync(temp_file.fileno())  # Ensure data is written to disk
        temp_file.close()
        temp_file_path = temp_file.name
        
        # Verify file was created
        if not os.path.exists(temp_file_path):
            logger.error(f"Failed to create temp file: {temp_file_path}")
            results['compilation'] = {
                'status': 'failed',
                'success': False,
                'errors': [f"Failed to create temp file: {temp_file_path}"],
            }
            return results
        
        try:
            # 1. Quality checks
            logger.info("Running quality checks...")
            is_valid, syntax_issues = self.qa.check_syntax(variant_code, source_file)
            security_issues = self.qa.check_security(variant_code, source_file)
            quality_score = self.qa.get_quality_score(variant_code)
            
            # Convert issues to dict, handling enums
            def issue_to_dict(issue):
                """Convert QualityIssue to dict, handling enums"""
                issue_dict = issue.__dict__.copy()
                if 'severity' in issue_dict and hasattr(issue_dict['severity'], 'value'):
                    issue_dict['severity'] = issue_dict['severity'].value
                return issue_dict
            
            results['quality'] = {
                'syntax_valid': is_valid,
                'syntax_issues': [issue_to_dict(issue) for issue in syntax_issues],
                'security_issues': [issue_to_dict(issue) for issue in security_issues],
                'quality_score': quality_score,
            }
            
            # Auto-fix if there are syntax errors or missing header warnings
            if not is_valid:
                has_errors = any(
                    hasattr(issue.severity, 'value') and issue.severity.value == 'error' 
                    or str(issue.severity) == 'IssueSeverity.ERROR'
                    for issue in syntax_issues
                )
                has_missing_headers = any(
                    'no such file' in issue.message.lower() or 
                    'fatal error' in issue.message.lower() or
                    'no such file or directory' in issue.message.lower()
                    for issue in syntax_issues
                )
                
                if auto_fix and (has_errors or has_missing_headers):
                    logger.warning("Syntax errors or missing headers detected")
                    logger.info("Attempting auto-fix...")
                    fixed_code, fix_success, _ = self.auto_fixer.fix_compilation_errors(
                        variant_code,
                        [issue.message for issue in syntax_issues],
                        language=self.language,
                        max_attempts=self.max_fix_attempts,
                    )
                    
                    if fix_success:
                        variant_code = fixed_code
                        results['fixed_code'] = fixed_code
                        # Rewrite temp file with fixed code
                        with open(temp_file_path, 'w') as f:
                            f.write(fixed_code)
                            f.flush()
                            os.fsync(f.fileno())  # Ensure data is written to disk
                        logger.info("✓ Auto-fix successful")
                        # Re-check syntax after fix
                        is_valid, syntax_issues = self.qa.check_syntax(variant_code, temp_file_path)
                        results['quality']['syntax_valid'] = is_valid
                        results['quality']['syntax_issues'] = [issue_to_dict(issue) for issue in syntax_issues]
                    else:
                        logger.warning("✗ Auto-fix failed")
            
            # 2. Compilation
            logger.info("Compiling...")
            compilation_result = self.compiler_pipeline.compile(temp_file_path)
            results['compilation'] = {
                'status': compilation_result.status.value,
                'success': compilation_result.status == CompilationStatus.SUCCESS,
                'errors': compilation_result.errors,
                'warnings': compilation_result.warnings,
                'executable': compilation_result.executable_path,
                'time': compilation_result.compilation_time,
            }
            
            if compilation_result.status == CompilationStatus.FAILED and auto_fix:
                logger.info("Compilation failed, attempting auto-fix...")
                fixed_code, fix_success, _ = self.auto_fixer.fix_compilation_errors(
                    variant_code,
                    compilation_result.errors,
                    language=self.language,
                    max_attempts=self.max_fix_attempts,
                )
                
                if fix_success:
                    variant_code = fixed_code
                    results['fixed_code'] = fixed_code
                    # Try compiling again
                    with open(temp_file_path, 'w') as f:
                        f.write(fixed_code)
                        f.flush()
                        os.fsync(f.fileno())  # Ensure data is written to disk
                    compilation_result = self.compiler_pipeline.compile(temp_file_path)
                    results['compilation']['status'] = compilation_result.status.value
                    results['compilation']['success'] = (
                        compilation_result.status == CompilationStatus.SUCCESS
                    )
                    results['compilation']['errors'] = compilation_result.errors
            
            # 3. Testing (if compilation successful)
            if (compilation_result.status == CompilationStatus.SUCCESS and 
                run_tests and 
                compilation_result.executable_path):
                logger.info("Running tests...")
                test_result = self.compiler_pipeline.test(compilation_result.executable_path)
                results['tests'] = {
                    'passed': test_result.passed,
                    'output': test_result.output,
                    'failures': test_result.failures,
                    'time': test_result.execution_time,
                }
            
            # 4. Functionality verification (if original code provided)
            if original_code:
                logger.info("Verifying functionality preservation...")
                preserves_func, func_issues = self.qa.verify_functionality(
                    original_code,
                    variant_code,
                )
                results['functionality'] = {
                    'preserved': preserves_func,
                    'issues': func_issues,
                }
            
            # Overall success
            results['success'] = (
                results['compilation']['success'] and
                (not run_tests or results.get('tests', {}).get('passed', True))
            )
            
            if results['success']:
                logger.info("✓ Variant processing successful")
            else:
                logger.warning("✗ Variant processing failed")
        
        finally:
            # Cleanup temp file (only if it exists and we created it)
            try:
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")
            
            # Cleanup compilation pipeline
            try:
                self.compiler_pipeline.cleanup()
            except Exception as e:
                logger.warning(f"Failed to cleanup compilation pipeline: {e}")
        
        return results

