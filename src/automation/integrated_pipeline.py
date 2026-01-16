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
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=os.path.splitext(source_file)[1],
            delete=False
        )
        temp_file.write(variant_code)
        temp_file.close()
        temp_file_path = temp_file.name
        
        try:
            # 1. Quality checks
            logger.info("Running quality checks...")
            is_valid, syntax_issues = self.qa.check_syntax(variant_code, source_file)
            security_issues = self.qa.check_security(variant_code, source_file)
            quality_score = self.qa.get_quality_score(variant_code)
            
            results['quality'] = {
                'syntax_valid': is_valid,
                'syntax_issues': [issue.__dict__ for issue in syntax_issues],
                'security_issues': [issue.__dict__ for issue in security_issues],
                'quality_score': quality_score,
            }
            
            if not is_valid:
                logger.warning("Syntax errors detected")
                if auto_fix:
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
                        logger.info("✓ Auto-fix successful")
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
            # Cleanup
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            self.compiler_pipeline.cleanup()
        
        return results

