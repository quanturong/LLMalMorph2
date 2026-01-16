"""
Example: Parallel Processing for Multiple Functions
"""
import asyncio
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParallelProcessor:
    """Parallel processing for function mutations"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    async def mutate_functions_async(
        self,
        functions: List[Dict],
        llm_provider,
        system_prompt: str,
    ) -> List[Dict]:
        """
        Mutate multiple functions in parallel using async.
        
        Args:
            functions: List of function dictionaries
            llm_provider: LLM provider instance
            system_prompt: System prompt for LLM
        
        Returns:
            List of mutation results
        """
        async def mutate_function(func: Dict) -> Dict:
            """Mutate a single function"""
            user_prompt = f"Mutate this function: {func['body']}"
            
            try:
                # Simulate async LLM call
                # In real implementation, use async LLM API
                response = await asyncio.to_thread(
                    llm_provider.generate,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                
                return {
                    "function": func["name"],
                    "success": True,
                    "response": response,
                }
            except Exception as e:
                logger.error(f"Error mutating {func['name']}: {e}")
                return {
                    "function": func["name"],
                    "success": False,
                    "error": str(e),
                }
        
        # Create tasks for all functions
        tasks = [mutate_function(func) for func in functions]
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    def mutate_functions_threaded(
        self,
        functions: List[Dict],
        llm_provider,
        system_prompt: str,
    ) -> List[Dict]:
        """
        Mutate multiple functions using thread pool.
        
        Args:
            functions: List of function dictionaries
            llm_provider: LLM provider instance
            system_prompt: System prompt for LLM
        
        Returns:
            List of mutation results
        """
        def mutate_function(func: Dict) -> Dict:
            """Mutate a single function"""
            user_prompt = f"Mutate this function: {func['body']}"
            
            try:
                response = llm_provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                
                return {
                    "function": func["name"],
                    "success": True,
                    "response": response,
                }
            except Exception as e:
                logger.error(f"Error mutating {func['name']}: {e}")
                return {
                    "function": func["name"],
                    "success": False,
                    "error": str(e),
                }
        
        # Use thread pool executor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(mutate_function, functions))
        
        return results
    
    def mutate_functions_sequential(
        self,
        functions: List[Dict],
        llm_provider,
        system_prompt: str,
    ) -> List[Dict]:
        """
        Mutate functions sequentially (baseline).
        
        Args:
            functions: List of function dictionaries
            llm_provider: LLM provider instance
            system_prompt: System prompt for LLM
        
        Returns:
            List of mutation results
        """
        results = []
        
        for func in functions:
            user_prompt = f"Mutate this function: {func['body']}"
            
            try:
                response = llm_provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                
                results.append({
                    "function": func["name"],
                    "success": True,
                    "response": response,
                })
            except Exception as e:
                logger.error(f"Error mutating {func['name']}: {e}")
                results.append({
                    "function": func["name"],
                    "success": False,
                    "error": str(e),
                })
        
        return results


def example_parallel_processing():
    """Example: Compare sequential vs parallel processing"""
    print("=" * 60)
    print("Parallel Processing Example")
    print("=" * 60)
    
    # Mock functions
    functions = [
        {"name": "add", "body": "int add(int a, int b) { return a + b; }"},
        {"name": "multiply", "body": "int multiply(int a, int b) { return a * b; }"},
        {"name": "subtract", "body": "int subtract(int a, int b) { return a - b; }"},
        {"name": "divide", "body": "int divide(int a, int b) { return a / b; }"},
    ]
    
    # Mock LLM provider (simulate delay)
    class MockLLM:
        def generate(self, system_prompt: str, user_prompt: str) -> str:
            time.sleep(1)  # Simulate API call delay
            return f"Mutated: {user_prompt}"
    
    llm = MockLLM()
    system_prompt = "You are a coding assistant"
    
    processor = ParallelProcessor(max_workers=4)
    
    # Sequential (baseline)
    print("\n1. Sequential Processing:")
    start = time.time()
    sequential_results = processor.mutate_functions_sequential(functions, llm, system_prompt)
    sequential_time = time.time() - start
    print(f"   Time: {sequential_time:.2f}s")
    print(f"   Success: {sum(1 for r in sequential_results if r['success'])}/{len(sequential_results)}")
    
    # Threaded
    print("\n2. Threaded Processing:")
    start = time.time()
    threaded_results = processor.mutate_functions_threaded(functions, llm, system_prompt)
    threaded_time = time.time() - start
    print(f"   Time: {threaded_time:.2f}s")
    print(f"   Success: {sum(1 for r in threaded_results if r['success'])}/{len(threaded_results)}")
    print(f"   Speedup: {sequential_time / threaded_time:.2f}x")
    
    # Async (would need async LLM provider)
    print("\n3. Async Processing:")
    print("   (Requires async LLM provider)")
    
    print("\n" + "=" * 60)
    print("✓ Parallel processing can significantly speed up mutations")
    print("=" * 60)


if __name__ == "__main__":
    example_parallel_processing()

