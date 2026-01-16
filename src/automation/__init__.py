"""
Automation module for LLMalMorph.
Provides automated compilation, testing, and error fixing.
"""
from .compilation_pipeline import (
    CompilationPipeline,
    CompilationResult,
    CompilationStatus,
    TestResult,
)
from .auto_fixer import AutoFixer
from .quality_assurance import (
    QualityAssurance,
    QualityIssue,
    IssueSeverity,
)
from .integrated_pipeline import IntegratedPipeline

__all__ = [
    'CompilationPipeline',
    'CompilationResult',
    'CompilationStatus',
    'TestResult',
    'AutoFixer',
    'QualityAssurance',
    'QualityIssue',
    'IssueSeverity',
    'IntegratedPipeline',
]

