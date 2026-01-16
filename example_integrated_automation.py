"""
Example: Using integrated automation pipeline
"""
import logging
import os
from src.automation import IntegratedPipeline
from src.config import get_config, setup_logging

# Setup logging
config = get_config()
setup_logging(config)
logger = logging.getLogger(__name__)


def example_automated_pipeline():
    """Example: Using integrated automation pipeline"""
    print("=" * 60)
    print("Integrated Automation Pipeline Example")
    print("=" * 60)
    
    # Create sample C code
    original_code = """
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    printf("Sum: %d\\n", add(2, 3));
    return 0;
}
"""
    
    # Variant with intentional error (for testing auto-fix)
    variant_code = """
#include <stdio.h>

int add(int a, int b) {
    return a + b;  // Optimized version
}

int main() {
    printf("Sum: %d\\n", add(2, 3));
    return 0;
}
"""
    
    # Write to temp files
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(variant_code)
        temp_file = f.name
    
    try:
        # Initialize pipeline
        pipeline = IntegratedPipeline(
            language="c",
            llm_model="codestral-2508",
            api_key=config.get_mistral_api_key(),
            max_fix_attempts=2,
        )
        
        # Process variant
        print("\nProcessing variant...")
        results = pipeline.process_variant(
            source_file=temp_file,
            variant_code=variant_code,
            original_code=original_code,
            auto_fix=True,
            run_tests=True,
        )
        
        # Print results
        print("\n" + "=" * 60)
        print("Results:")
        print("=" * 60)
        
        print(f"\nCompilation:")
        comp = results['compilation']
        print(f"  Status: {comp['status']}")
        print(f"  Success: {comp['success']}")
        if comp['errors']:
            print(f"  Errors: {len(comp['errors'])}")
            for error in comp['errors'][:3]:
                print(f"    - {error}")
        
        print(f"\nQuality:")
        quality = results['quality']
        print(f"  Syntax Valid: {quality['syntax_valid']}")
        print(f"  Quality Score: {quality['quality_score']:.2f}")
        print(f"  Security Issues: {len(quality['security_issues'])}")
        
        if results.get('tests'):
            tests = results['tests']
            print(f"\nTests:")
            print(f"  Passed: {tests['passed']}")
            if tests['failures']:
                print(f"  Failures: {tests['failures']}")
        
        if results.get('functionality'):
            func = results['functionality']
            print(f"\nFunctionality:")
            print(f"  Preserved: {func['preserved']}")
            if func['issues']:
                print(f"  Issues: {func['issues']}")
        
        print(f"\nOverall Success: {results['success']}")
        print("=" * 60)
    
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == "__main__":
    example_automated_pipeline()

