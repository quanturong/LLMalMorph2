"""
Example usage of improved LLMalMorph system.
"""
import os
import logging
from src.config import get_config, setup_logging
from src.llm_api import get_llm_provider, LLMAPIError
from src.pipeline_util_improved import run_experiment_trial

# Setup logging
config = get_config()
setup_logging(config)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Example: Basic LLM API usage"""
    print("=" * 60)
    print("Example 1: Basic LLM API Usage")
    print("=" * 60)
    
    # Get provider (automatically selects based on model name)
    try:
        # Mistral API example
        provider = get_llm_provider("codestral-2508")
        
        response = provider.generate(
            system_prompt="You are a helpful coding assistant.",
            user_prompt="Write a Python function that adds two numbers.",
            model="codestral-2508",
            seed=42,
        )
        
        print("Response:")
        print(response[:200] + "..." if len(response) > 200 else response)
        
    except LLMAPIError as e:
        logger.error(f"API Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def example_experiment_trial():
    """Example: Running an experiment trial"""
    print("\n" + "=" * 60)
    print("Example 2: Running Experiment Trial")
    print("=" * 60)
    
    # Make sure output directory exists
    output_dir = "./example_output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        response, response_time = run_experiment_trial(
            llm="codestral-2508",
            system_prompt="You are an expert C programmer.",
            user_prompt="Write a function to calculate factorial.",
            trial_no=0,
            llm_response_sub_dir_final=output_dir,
            language_name="Language: c\n",
            source_file_name="example.c",
            num_functions=1,
            seed=42,
            batch_num=1,
            api_key=config.get_mistral_api_key(),
        )
        
        print(f"✓ Experiment completed in {response_time:.2f} seconds")
        print(f"✓ Response saved to {output_dir}")
        
    except LLMAPIError as e:
        logger.error(f"API Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def example_with_fallback():
    """Example: Using fallback when primary provider fails"""
    print("\n" + "=" * 60)
    print("Example 3: Fallback Mechanism")
    print("=" * 60)
    
    providers = [
        ("codestral-2508", "Mistral API"),
        ("codellama:7b-instruct", "Ollama"),
    ]
    
    for model_name, provider_name in providers:
        try:
            print(f"\nTrying {provider_name} ({model_name})...")
            provider = get_llm_provider(model_name)
            
            response = provider.generate(
                system_prompt="You are a helpful assistant.",
                user_prompt="Say hello in one sentence.",
                model=model_name,
            )
            
            print(f"✓ Success with {provider_name}")
            print(f"Response: {response[:100]}...")
            break  # Success, no need to try fallback
            
        except LLMAPIError as e:
            print(f"✗ Failed with {provider_name}: {e}")
            continue  # Try next provider
    else:
        print("✗ All providers failed")


if __name__ == "__main__":
    # Check if API key is set
    api_key = config.get_mistral_api_key()
    if not api_key:
        print("⚠️  Warning: MISTRAL_API_KEY not set. Mistral API calls will fail.")
        print("   Set it with: export MISTRAL_API_KEY='your-key'")
        print()
    
    # Run examples
    try:
        example_basic_usage()
        example_experiment_trial()
        example_with_fallback()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        logger.exception("Unexpected error in examples")

