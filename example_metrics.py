"""
Example: Metrics Collection and Analytics
"""
import time
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MutationMetrics:
    """Metrics for a single mutation"""
    function_name: str
    start_time: float
    end_time: float
    success: bool
    llm_response_time: float
    compilation_success: Optional[bool] = None
    compilation_time: Optional[float] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def total_time(self) -> float:
        return self.end_time - self.start_time


class MetricsCollector:
    """Collect and analyze mutation metrics"""
    
    def __init__(self):
        self.metrics: List[MutationMetrics] = []
        self.session_start = time.time()
    
    def record_mutation(
        self,
        function_name: str,
        success: bool,
        llm_response_time: float,
        compilation_success: Optional[bool] = None,
        compilation_time: Optional[float] = None,
        errors: List[str] = None,
    ):
        """Record mutation metrics"""
        metric = MutationMetrics(
            function_name=function_name,
            start_time=time.time() - llm_response_time,
            end_time=time.time(),
            success=success,
            llm_response_time=llm_response_time,
            compilation_success=compilation_success,
            compilation_time=compilation_time,
            errors=errors or [],
        )
        self.metrics.append(metric)
        logger.debug(f"Recorded metrics for {function_name}")
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.metrics:
            return {"message": "No metrics collected"}
        
        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        failed = total - successful
        
        avg_llm_time = sum(m.llm_response_time for m in self.metrics) / total
        avg_total_time = sum(m.total_time for m in self.metrics) / total
        
        compilation_stats = {}
        compilation_metrics = [m for m in self.metrics if m.compilation_success is not None]
        if compilation_metrics:
            compilation_stats = {
                "total_compiled": len(compilation_metrics),
                "compilation_success_rate": sum(1 for m in compilation_metrics if m.compilation_success) / len(compilation_metrics),
                "avg_compilation_time": sum(m.compilation_time for m in compilation_metrics if m.compilation_time) / len(compilation_metrics),
            }
        
        return {
            "total_mutations": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total,
            "avg_llm_response_time": avg_llm_time,
            "avg_total_time": avg_total_time,
            "total_session_time": time.time() - self.session_start,
            "compilation": compilation_stats,
        }
    
    def get_function_stats(self) -> Dict[str, Dict]:
        """Get statistics per function"""
        function_stats = defaultdict(lambda: {
            "count": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0,
            "avg_time": 0,
        })
        
        for metric in self.metrics:
            stats = function_stats[metric.function_name]
            stats["count"] += 1
            if metric.success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
            stats["total_time"] += metric.total_time
        
        # Calculate averages
        for stats in function_stats.values():
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["success_rate"] = stats["successful"] / stats["count"]
        
        return dict(function_stats)
    
    def export_json(self, filepath: str):
        """Export metrics to JSON file"""
        data = {
            "summary": self.get_summary(),
            "function_stats": self.get_function_stats(),
            "detailed_metrics": [asdict(m) for m in self.metrics],
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported metrics to {filepath}")
    
    def print_report(self):
        """Print metrics report"""
        summary = self.get_summary()
        function_stats = self.get_function_stats()
        
        print("\n" + "=" * 60)
        print("Mutation Metrics Report")
        print("=" * 60)
        
        print(f"\nOverall Statistics:")
        print(f"  Total Mutations: {summary['total_mutations']}")
        print(f"  Successful: {summary['successful']} ({summary['success_rate']*100:.1f}%)")
        print(f"  Failed: {summary['failed']}")
        print(f"  Avg LLM Response Time: {summary['avg_llm_response_time']:.2f}s")
        print(f"  Avg Total Time: {summary['avg_total_time']:.2f}s")
        print(f"  Total Session Time: {summary['total_session_time']:.2f}s")
        
        if summary.get("compilation"):
            comp = summary["compilation"]
            print(f"\nCompilation Statistics:")
            print(f"  Total Compiled: {comp['total_compiled']}")
            print(f"  Success Rate: {comp['compilation_success_rate']*100:.1f}%")
            print(f"  Avg Compilation Time: {comp['avg_compilation_time']:.2f}s")
        
        if function_stats:
            print(f"\nPer-Function Statistics:")
            for func_name, stats in function_stats.items():
                print(f"  {func_name}:")
                print(f"    Count: {stats['count']}")
                print(f"    Success Rate: {stats['success_rate']*100:.1f}%")
                print(f"    Avg Time: {stats['avg_time']:.2f}s")
        
        print("=" * 60)


def example_metrics_collection():
    """Example: Collect and analyze metrics"""
    print("=" * 60)
    print("Metrics Collection Example")
    print("=" * 60)
    
    collector = MetricsCollector()
    
    # Simulate some mutations
    functions = ["add", "multiply", "subtract", "divide"]
    
    for func in functions:
        # Simulate mutation
        llm_time = 1.5 + (hash(func) % 100) / 100  # Random time
        success = hash(func) % 10 > 1  # 80% success rate
        
        compilation_success = None
        compilation_time = None
        if success:
            compilation_success = hash(func) % 10 > 2  # 70% compilation success
            if compilation_success:
                compilation_time = 0.5 + (hash(func) % 50) / 100
        
        errors = [] if success else ["LLM generation failed"]
        
        collector.record_mutation(
            function_name=func,
            success=success,
            llm_response_time=llm_time,
            compilation_success=compilation_success,
            compilation_time=compilation_time,
            errors=errors,
        )
        
        time.sleep(0.1)  # Simulate processing time
    
    # Print report
    collector.print_report()
    
    # Export to JSON
    collector.export_json("metrics_example.json")
    print("\n✓ Metrics exported to metrics_example.json")


if __name__ == "__main__":
    example_metrics_collection()

