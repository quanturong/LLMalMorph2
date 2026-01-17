"""
Unified LLM API interface supporting both Ollama (local) and Mistral API (cloud).
Provides error handling, retry mechanism, and logging.
"""
import os
import time
import logging
import requests
from typing import Optional, Dict, Any
from functools import wraps

# Optional imports for Ollama (not needed on Kaggle)
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# Configure logging
logger = logging.getLogger(__name__)


class LLMAPIError(Exception):
    """Base exception for LLM API errors"""
    pass


class LLMAPIKeyError(LLMAPIError):
    """Raised when API key is missing or invalid"""
    pass


class LLMAPIRequestError(LLMAPIError):
    """Raised when API request fails"""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying API calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, LLMAPIRequestError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                            f"Retrying in {current_delay:.2f} seconds..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"API call failed after {max_retries + 1} attempts")
                except Exception as e:
                    # Don't retry on non-retryable errors
                    logger.error(f"Non-retryable error: {str(e)}")
                    raise
            
            raise LLMAPIRequestError(f"Failed after {max_retries + 1} attempts: {str(last_exception)}")
        
        return wrapper
    return decorator


class LLMProvider:
    """Base class for LLM providers"""
    
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Generate response from LLM.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            **kwargs: Additional parameters (seed, temperature, etc.)
        
        Returns:
            Generated text response
        
        Raises:
            LLMAPIError: If generation fails
        """
        raise NotImplementedError


class MistralAPIProvider(LLMProvider):
    """Mistral API provider (Codestral)"""
    
    BASE_URL = "https://api.mistral.ai/v1/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Mistral API provider.
        
        Args:
            api_key: Mistral API key. If None, reads from MISTRAL_API_KEY env var.
        
        Raises:
            LLMAPIKeyError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise LLMAPIKeyError(
                "Mistral API key not found. Please set MISTRAL_API_KEY environment variable "
                "or provide api_key parameter."
            )
        
        logger.info("Mistral API provider initialized")
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "codestral-latest",
        temperature: float = 0.7,
        top_p: float = 0.9,
        seed: Optional[int] = None,
        timeout: int = 60,
        **kwargs
    ) -> str:
        """
        Generate response using Mistral API.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name (e.g., "codestral-latest", "codestral-2508")
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            seed: Random seed for reproducibility
            timeout: Request timeout in seconds
            **kwargs: Additional parameters (ignored for Mistral API)
        
        Returns:
            Generated text response
        
        Raises:
            LLMAPIRequestError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        data: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        
        if seed is not None:
            data["random_seed"] = seed
        
        logger.debug(f"Calling Mistral API with model: {model}, seed: {seed}")
        start_time = time.time()
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            
            result = response.json()
            elapsed_time = time.time() - start_time
            
            if "choices" not in result or len(result["choices"]) == 0:
                raise LLMAPIRequestError("Invalid response format from Mistral API")
            
            content = result["choices"][0]["message"]["content"]
            
            logger.info(
                f"Mistral API call successful. Model: {model}, "
                f"Time: {elapsed_time:.2f}s, "
                f"Tokens: {result.get('usage', {}).get('total_tokens', 'N/A')}"
            )
            
            return content
            
        except requests.exceptions.Timeout:
            raise LLMAPIRequestError(f"Request timeout after {timeout} seconds")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise LLMAPIKeyError("Invalid Mistral API key")
            elif e.response.status_code == 429:
                raise LLMAPIRequestError("Rate limit exceeded. Please try again later.")
            else:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                raise LLMAPIRequestError(error_msg)
        except requests.exceptions.RequestException as e:
            raise LLMAPIRequestError(f"Request failed: {str(e)}")


class DeepSeekProvider(LLMProvider):
    """DeepSeek API provider (OpenAI-compatible)"""
    
    BASE_URL = "https://api.deepseek.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepSeek API provider.
        
        Args:
            api_key: DeepSeek API key. If None, reads from DEEPSEEK_API_KEY env var.
        
        Raises:
            LLMAPIKeyError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise LLMAPIKeyError(
                "DeepSeek API key not found. Please set DEEPSEEK_API_KEY environment variable "
                "or provide api_key parameter."
            )
        
        if not OPENAI_AVAILABLE:
            raise LLMAPIError(
                "OpenAI library is required for DeepSeek API. Install with: pip install openai"
            )
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.BASE_URL)
        logger.info("DeepSeek API provider initialized")
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "deepseek-coder",
        temperature: float = 0.7,
        top_p: float = 0.9,
        seed: Optional[int] = None,
        timeout: int = 120,
        **kwargs
    ) -> str:
        """
        Generate response using DeepSeek API.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name (e.g., "deepseek-coder", "deepseek-chat")
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            seed: Random seed for reproducibility
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
        
        Returns:
            Generated text response
        
        Raises:
            LLMAPIRequestError: If API request fails
        """
        logger.debug(f"Calling DeepSeek API with model: {model}, seed: {seed}")
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                top_p=top_p,
                seed=seed,
                timeout=timeout,
            )
            
            elapsed_time = time.time() - start_time
            content = response.choices[0].message.content
            
            logger.info(
                f"DeepSeek API call successful. Model: {model}, "
                f"Time: {elapsed_time:.2f}s, "
                f"Tokens: {response.usage.total_tokens if response.usage else 'N/A'}"
            )
            
            return content
            
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise LLMAPIKeyError("Invalid DeepSeek API key")
            elif "429" in error_msg or "rate" in error_msg.lower():
                raise LLMAPIRequestError("Rate limit exceeded. Please try again later.")
            else:
                raise LLMAPIRequestError(f"DeepSeek API call failed: {error_msg}")


class OllamaProvider(LLMProvider):
    """Ollama local provider"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Ollama server URL
        
        Raises:
            LLMAPIError: If Ollama is not available
        """
        if not OLLAMA_AVAILABLE:
            raise LLMAPIError(
                "Ollama is not available. Install with: pip install ollama"
            )
        self.base_url = base_url
        logger.info(f"Ollama provider initialized with base_url: {base_url}")
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "codestral:latest",
        temperature: float = 0.8,
        top_k: int = 40,
        top_p: float = 0.9,
        seed: Optional[int] = 42,
        **kwargs
    ) -> str:
        """
        Generate response using Ollama.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            model: Model name
            temperature: Sampling temperature
            top_k: Top-k sampling parameter
            top_p: Top-p sampling parameter
            seed: Random seed for reproducibility
            **kwargs: Additional parameters (ignored)
        
        Returns:
            Generated text response
        
        Raises:
            LLMAPIRequestError: If API request fails
        """
        logger.debug(f"Calling Ollama with model: {model}, seed: {seed}")
        start_time = time.time()
        
        if not OLLAMA_AVAILABLE:
            raise LLMAPIError("Ollama is not available. Install with: pip install ollama")
        
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                    "seed": seed,
                },
            )
            
            elapsed_time = time.time() - start_time
            content = response["message"]["content"]
            
            logger.info(
                f"Ollama call successful. Model: {model}, "
                f"Time: {elapsed_time:.2f}s"
            )
            
            return content
            
        except Exception as e:
            raise LLMAPIRequestError(f"Ollama API call failed: {str(e)}")


def get_llm_provider(model_name: str, api_key: Optional[str] = None) -> LLMProvider:
    """
    Factory function to get appropriate LLM provider based on model name.
    
    Args:
        model_name: Model name (e.g., "codestral-2508", "codestral:latest", "deepseek-coder")
        api_key: Optional API key (if None, reads from env)
    
    Returns:
        LLMProvider instance
    
    Raises:
        ValueError: If model name format is unrecognized
    """
    # Check if it's a DeepSeek API model
    if model_name.startswith("deepseek-") and model_name in ["deepseek-coder", "deepseek-chat"]:
        return DeepSeekProvider(api_key=api_key)
    
    # Check if it's a Mistral API model (codestral-* or codestral-latest)
    if model_name.startswith("codestral-") or model_name == "codestral-latest":
        # Normalize model name (remove colons, use dashes)
        normalized_model = model_name.replace(":", "-")
        return MistralAPIProvider(api_key=api_key)
    
    # Default to Ollama for other models
    return OllamaProvider()


def ollama_chat_api(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    seed: int = 42,
    api_key: Optional[str] = None,
) -> str:
    """
    Unified API function for backward compatibility.
    Automatically selects appropriate provider based on model name.
    
    Args:
        model_name: Model name
        system_prompt: System prompt
        user_prompt: User prompt
        seed: Random seed
        api_key: Optional API key for Mistral
    
    Returns:
        Generated text response
    
    Raises:
        LLMAPIError: If generation fails
    """
    try:
        provider = get_llm_provider(model_name, api_key=api_key)
        
        # Normalize model name for Mistral API
        if isinstance(provider, MistralAPIProvider):
            model = model_name.replace(":", "-")
        else:
            model = model_name
        
        return provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            seed=seed,
        )
    except LLMAPIError:
        raise
    except Exception as e:
        raise LLMAPIError(f"Unexpected error: {str(e)}")


def print_model_names():
    """Print available models (Ollama only, Mistral models are fixed)"""
    if OLLAMA_AVAILABLE:
        try:
            models = ollama.list()["models"]
            print("Available Ollama models:")
            for model in models:
                print(f"  - {model['name']}")
        except Exception as e:
            logger.warning(f"Could not list Ollama models: {str(e)}")
    else:
        print("Ollama is not available. Install with: pip install ollama")
    
    print("\nAvailable Mistral API models:")
    print("  - codestral-latest")
    print("  - codestral-2508")

