#!/usr/bin/env python3
"""
Example: Meta-agent MVP demonstration

Shows how the meta-agent decomposes a high-level task, executes sub-tasks,
verifies results, and recombines into final solution.
"""

from src.meta_agent import (
    MetaAgent, Task, TaskDecomposer, TaskExecutor, TaskVerifier, ResultCombiner
)
import json


def print_tree(task: Task, indent: int = 0):
    """Print task execution tree."""
    prefix = "  " * indent
    status_symbol = {
        "pending": "|",
        "executing": ">",
        "completed": "✓",
        "verified": "✓✓",
        "failed": "x"
    }.get(task.status, "?")
    
    print(f"{prefix}{status_symbol} [{task.id}] {task.description[:60]}")
    if task.result:
        print(f"{prefix}   -> {task.result.get('output', 'No output')[:50]}")
    
    for sub_task in task.sub_tasks:
        print_tree(sub_task, indent + 1)


def example_1_simple_decomposition():
    print("EXAMPLE 1: Simple Task Decomposition")
    
    # Create components
    decomposer = TaskDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    # Create meta-agent
    meta_agent = MetaAgent(
        decomposer=decomposer,
        executor=executor,
        verifier=verifier,
        combiner=combiner,
        max_depth=3
    )
    
    # Define task
    task = Task(
        id="task-1",
        description="Fetch user profile and validate email address and check account status",
        inputs={"user_id": "12345"},
        verification_criteria=["profile", "email", "status"]
    )
    
    print("TASK DESCRIPTION:")
    print(f"  {task.description}")
    print(f"  Inputs: {task.inputs}")
    print(f"  Verification: {task.verification_criteria}")
    
    # Solve
    print("\nEXECUTION:")
    result = meta_agent.solve(task)
    
    print("\nFINAL RESULT:")
    print(f"  Verified: {result['verified']}")
    print(f"  Result: {json.dumps(result['result'], indent=2)}")
    
    print("\nEXECUTION TREE:")
    print_tree(result['execution_tree'])
    
    print("\nSTATISTICS:")
    print(f"  Total log entries: {len(result['logs'])}")
    print(f"  Executions: {executor.execution_count}")
    print(f"  Verifications: {verifier.verification_count}")
    print(f"  Combinations: {combiner.combination_count}")


def example_2_sequential_tasks():
    print("EXAMPLE 2: Sequential Task Chain")
    
    # Create components
    decomposer = TaskDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    # Create meta-agent
    meta_agent = MetaAgent(
        decomposer=decomposer,
        executor=executor,
        verifier=verifier,
        combiner=combiner,
        max_depth=3
    )
    
    # Define task
    task = Task(
        id="task-2",
        description="Load customer order then validate payment details then process refund then send confirmation email",
        inputs={"order_id": "ORD-789"},
        verification_criteria=["order loaded", "payment validated", "refund processed", "email sent"]
    )
    
    print("TASK DESCRIPTION:")
    print(f"  {task.description}")
    print(f"  Inputs: {task.inputs}")
    
    # Solve
    print("\nEXECUTION:")
    result = meta_agent.solve(task)
    
    print("\nFINAL RESULT:")
    print(f"  Verified: {result['verified']}")
    print(f"  Result: {json.dumps(result['result'], indent=2)}")
    
    print("\nEXECUTION TREE:")
    print_tree(result['execution_tree'])


def example_3_nested_decomposition():
    print("EXAMPLE 3: Nested Task Decomposition")
    
    # Create components with manual decomposition for deeper nesting
    # I like the idea of making this pattern more general and reusable,
    # but for now it is problem-specific.
    class NestedDecomposer(TaskDecomposer):
        """Custom decomposer that creates nested structure"""
        
        def decompose(self, task: Task, depth: int):
            # Force decomposition for demo purposes
            if "process order" in task.description.lower():
                from src.meta_agent import DecompositionResult
                
                # Create two sub-tasks, one of which will decompose further
                sub_tasks = [
                    Task(
                        id=f"{task.id}.1",
                        description="Validate customer details and check inventory status",
                        inputs=task.inputs,
                        parent_id=task.id,
                        is_atomic=False  # Will decompose further
                    ),
                    Task(
                        id=f"{task.id}.2",
                        description="Calculate shipping cost then reserve inventory",
                        inputs=task.inputs,
                        parent_id=task.id,
                        is_atomic=False  # Will decompose further
                    )
                ]
                
                return DecompositionResult(
                    sub_tasks=sub_tasks,
                    decomposition_strategy="sequential",
                    recombination_plan="Chain: pass output of each task as input to next",
                    reasoning="Split order processing into validation and shipping"
                )
            
            # Use parent decomposition for other tasks
            return super().decompose(task, depth)
    
    decomposer = NestedDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    # Create meta-agent
    meta_agent = MetaAgent(
        decomposer=decomposer,
        executor=executor,
        verifier=verifier,
        combiner=combiner,
        max_depth=5
    )
    
    # Define complex task
    task = Task(
        id="task-3",
        description="Process customer order with priority shipping",
        inputs={"order_id": "ORD-999", "customer_id": "CUST-456"},
        verification_criteria=["order processed"]
    )
    
    print("TASK DESCRIPTION:")
    print(f"  {task.description}")
    print(f"  Inputs: {task.inputs}")
    
    # Solve
    print("\nEXECUTION:")
    result = meta_agent.solve(task)
    
    print("\nFINAL RESULT:")
    print(f"  Verified: {result['verified']}")
    
    print("\nEXECUTION TREE (showing recursive decomposition):")
    print_tree(result['execution_tree'])
    
    print("\nDECOMPOSITION HISTORY:")
    for i, entry in enumerate(decomposer.decomposition_history):
        print(f"  Level {entry['depth']}: {entry['task'].id} -> {len(entry['result'].sub_tasks)} sub-tasks")


def example_4_atomic_task():
    print("EXAMPLE 4: Atomic Task (No Decomposition)")
    
    decomposer = TaskDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    meta_agent = MetaAgent(
        decomposer=decomposer,
        executor=executor,
        verifier=verifier,
        combiner=combiner,
        max_depth=3
    )
    
    # Simple atomic task
    task = Task(
        id="task-4",
        description="Calculate total price for items in cart",
        inputs={"cart_items": [{"price": 10}, {"price": 20}, {"price": 15}]},
        is_atomic=True,
        verification_criteria=["total"]
    )
    
    print("TASK DESCRIPTION:")
    print(f"  {task.description}")
    print(f"  Marked as atomic: {task.is_atomic}")
    
    # Solve
    print("\nEXECUTION:")
    result = meta_agent.solve(task)
    
    print("\nFINAL RESULT:")
    print(f"  Verified: {result['verified']}")
    print(f"  Execution time: {task.execution_time:.4f}s")
    print(f"  Result: {json.dumps(result['result'], indent=2)}")
    
    print("\nNOTE: Task executed directly without decomposition")


def main():
    """Run all examples"""
    print("META-AGENT MVP DEMONSTRATION")
    
    try:
        example_1_simple_decomposition()
        input("Press Enter to continue to Example 2...")
        
        example_2_sequential_tasks()
        input("Press Enter to continue to Example 3...")
        
        example_3_nested_decomposition()
        input("Press Enter to continue to Example 4...")
        
        example_4_atomic_task()
        
        print("\n====== ALL EXAMPLES COMPLETED ======")
        
    except Exception as e:
        print(f"\n Error during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
