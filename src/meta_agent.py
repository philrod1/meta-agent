"""
Meta-agent that decomposes tasks, executes sub-tasks, and recombines results.

The meta-agent follows this cycle:
1. Receive high-level task specification
2. Decompose into simpler, verifiable sub-tasks
3. Execute each sub-task
4. Verify each sub-task result
5. Recombine all results into final solution
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class Task:
    """Represents a task at any level of decomposition."""
    id: str
    description: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    is_atomic: bool = False  # True if task cannot be decomposed further
    verification_criteria: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    
    # Execution state
    status: str = "pending"  # pending, executing, completed, failed, verified
    result: Optional[Dict[str, Any]] = None
    sub_tasks: List['Task'] = field(default_factory=list)
    execution_time: float = 0.0
    verification_log: List[str] = field(default_factory=list)


@dataclass
class DecompositionResult:
    """Result of decomposing a task."""
    sub_tasks: List[Task]
    decomposition_strategy: str  # e.g., "sequential", "parallel", "hierarchical"
    recombination_plan: str      # How to merge sub-task results
    reasoning: str               # Why this decomposition was chosen


class MetaAgent:
    """
    Meta-agent that orchestrates task decomposition, execution, and recombination.
    
    This is the top-level orchestrator that decides:
    - Whether a task needs decomposition
    - How to decompose tasks into sub-tasks
    - When tasks are simple enough to execute directly
    - How to verify results
    - How to recombine sub-results into final answer
    """
    
    def __init__(self, decomposer, executor, verifier, combiner, max_depth: int = 5):
        """
        Args:
            decomposer: Service that breaks tasks into sub-tasks
            executor: Service that executes atomic tasks
            verifier: Service that validates task results
            combiner: Service that merges sub-task results
        """
        self.decomposer = decomposer
        self.executor = executor
        self.verifier = verifier
        self.combiner = combiner
        self.execution_log: List[Dict[str, Any]] = []
        
    def solve(self, task: Task, depth: int = 0) -> Dict[str, Any]:
        """
        Main entry point: solve a task by decomposing, executing, and recombining.
        
        Returns:
            Dict with 'result', 'verified', 'execution_tree', 'logs'
        """
        self._log(f"{'  ' * depth}[META] Solving task: {task.id} - {task.description[:60]}...")
        
        # Base case: atomic task (something simple enough to reason about)
        if task.is_atomic:
            self._log(f"{'  ' * depth}[META] Task is atomic, executing directly")
            return self._execute_atomic_task(task, depth)
        
        # Recursive case: decompose into sub-tasks
        try:
            decomposition = self.decomposer.decompose(task, depth)
            
            if not decomposition.sub_tasks:
                # If decomposition produces no sub-tasks, treat as atomic
                self._log(f"{'  ' * depth}[META] No sub-tasks generated, executing as atomic")
                return self._execute_atomic_task(task, depth)
            
            self._log(f"{'  ' * depth}[META] Decomposed into {len(decomposition.sub_tasks)} sub-tasks")
            self._log(f"{'  ' * depth}[META] Strategy: {decomposition.decomposition_strategy}")
            
            # Store sub-tasks in parent
            task.sub_tasks = decomposition.sub_tasks
            
            # Recursively solve each sub-task
            sub_results = []
            for i, sub_task in enumerate(decomposition.sub_tasks):
                self._log(f"{'  ' * depth}[META] Solving sub-task {i+1}/{len(decomposition.sub_tasks)}")
                sub_result = self.solve(sub_task, depth + 1)
                sub_results.append(sub_result)
                
                # Early termination if critical sub-task fails
                if not sub_result['verified']:
                    self._log(f"{'  ' * depth}[META] Sub-task {i+1} failed verification, aborting")
                    return {
                        'result': None,
                        'verified': False,
                        'execution_tree': task,
                        'logs': self.execution_log,
                        'error': f"Sub-task {sub_task.id} failed"
                    }
            
            # Recombine sub-task results
            self._log(f"{'  ' * depth}[META] Recombining {len(sub_results)} sub-results")
            combined_result = self.combiner.combine(
                task=task,
                sub_tasks=decomposition.sub_tasks,
                sub_results=sub_results,
                recombination_plan=decomposition.recombination_plan
            )
            
            # Verify combined result
            task.result = combined_result
            task.status = "completed"
            verification = self.verifier.verify(task)
            
            self._log(f"{'  ' * depth}[META] Task {task.id} completed, verified={verification['valid']}")
            
            return {
                'result': combined_result,
                'verified': verification['valid'],
                'execution_tree': task,
                'logs': self.execution_log,
                'verification': verification
            }
            
        except Exception as e:
            self._log(f"{'  ' * depth}[META] Error: {str(e)}")
            task.status = "failed"
            return {
                'result': None,
                'verified': False,
                'execution_tree': task,
                'logs': self.execution_log,
                'error': str(e)
            }
    
    def _execute_atomic_task(self, task: Task, depth: int) -> Dict[str, Any]:
        """Execute a single atomic task without further decomposition."""
        self._log(f"{'  ' * depth}[EXEC] Executing atomic task: {task.id}")
        
        start_time = time.time()
        task.status = "executing"
        
        try:
            # Execute the task
            result = self.executor.execute(task)
            task.result = result
            task.execution_time = time.time() - start_time
            task.status = "completed"
            
            # Verify the result
            verification = self.verifier.verify(task)
            task.verification_log = verification.get('log', [])
            
            if verification['valid']:
                task.status = "verified"
                self._log(f"{'  ' * depth}[EXEC] Task {task.id} verified successfully")
            else:
                self._log(f"{'  ' * depth}[EXEC] Task {task.id} verification failed")
            
            return {
                'result': result,
                'verified': verification['valid'],
                'execution_tree': task,
                'logs': self.execution_log,
                'verification': verification
            }
            
        except Exception as e:
            task.status = "failed"
            task.execution_time = time.time() - start_time
            self._log(f"{'  ' * depth}[EXEC] Task {task.id} failed: {str(e)}")
            
            return {
                'result': None,
                'verified': False,
                'execution_tree': task,
                'logs': self.execution_log,
                'error': str(e)
            }
    
    def _log(self, message: str):
        """Add a message to execution log."""
        log_entry = {
            'timestamp': time.time(),
            'message': message
        }
        self.execution_log.append(log_entry)
        print(message)  # Also print for real-time feedback


class TaskDecomposer:
    """
    Decomposes high-level tasks into simpler, verifiable sub-tasks.

    Uses LLM or heuristics to analyse task and produce decomposition plan.
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.decomposition_history = []
    
    def decompose(self, task: Task, depth: int) -> DecompositionResult:
        """
        Break down a task into sub-tasks.
        
        Returns DecompositionResult with sub-tasks and recombination plan.
        """
        # For MVP, use rule-based decomposition
        # In production, this could be an LLM with decomposition prompts
        
        if self._is_simple_enough(task):
            # Task is already simple enough
            return DecompositionResult(
                sub_tasks=[],
                decomposition_strategy="none",
                recombination_plan="direct",
                reasoning="Task is already atomic"
            )
        
        # Apply decomposition heuristics based on task description
        sub_tasks = self._heuristic_decompose(task, depth)
        
        strategy = self._determine_strategy(sub_tasks)
        recombination_plan = self._create_recombination_plan(task, sub_tasks, strategy)
        
        result = DecompositionResult(
            sub_tasks=sub_tasks,
            decomposition_strategy=strategy,
            recombination_plan=recombination_plan,
            reasoning=f"Decomposed into {len(sub_tasks)} sub-tasks using {strategy} strategy"
        )
        
        self.decomposition_history.append({
            'task': task,
            'result': result,
            'depth': depth
        })
        
        return result
    
    def _is_simple_enough(self, task: Task) -> bool:
        """Determine if task is simple enough to execute without further decomposition."""
        # Simple heuristics for MVP
        if task.is_atomic:
            return True
        
        # Check if description suggests it's a single action
        simple_keywords = ['calculate', 'fetch', 'validate', 'check', 'send', 'get', 'set']
        desc_lower = task.description.lower()
        
        return any(keyword in desc_lower and desc_lower.count(' and ') == 0 
                   for keyword in simple_keywords)
    
    def _heuristic_decompose(self, task: Task, depth: int) -> List[Task]:
        """Use heuristics to decompose task."""
        # For MVP: look for indicators
        desc = task.description.lower()
        
        sub_tasks = []
        
        # Split on "and" for parallel tasks
        if ' and ' in desc:
            parts = task.description.split(' and ')
            for i, part in enumerate(parts):
                sub_tasks.append(Task(
                    id=f"{task.id}.{i+1}",
                    description=part.strip(),
                    inputs=task.inputs,
                    is_atomic=True,
                    parent_id=task.id,
                    verification_criteria=[]
                ))
        
        # Split on "then" for sequential tasks
        elif ' then ' in desc:
            parts = task.description.split(' then ')
            for i, part in enumerate(parts):
                sub_tasks.append(Task(
                    id=f"{task.id}.{i+1}",
                    description=part.strip(),
                    inputs=task.inputs if i == 0 else {},  # Only first task gets inputs
                    is_atomic=True,
                    parent_id=task.id,
                    verification_criteria=[]
                ))
        
        # If no obvious decomposition, mark as atomic
        if not sub_tasks:
            return []
        
        return sub_tasks
    
    def _determine_strategy(self, sub_tasks: List[Task]) -> str:
        """Determine execution strategy for sub-tasks."""
        if not sub_tasks:
            return "none"
        
        # If tasks reference each other's outputs, sequential
        # Otherwise, parallel.
        # The MVP isn't that sophisticated yet, so ...
        return "sequential"
    
    def _create_recombination_plan(self, task: Task, sub_tasks: List[Task], strategy: str) -> str:
        """Create plan for how to recombine sub-task results."""
        if strategy == "sequential":
            return "Chain: pass output of each task as input to next, return final output"
        elif strategy == "parallel":
            return "Merge: combine all outputs into single result dict"
        else:
            return "Direct: return single result"


class TaskExecutor:
    """
    Executes atomic tasks that cannot be decomposed further.
    
    May create and run workflows, call tools, or invoke LLMs.
    """
    
    def __init__(self, tool_registry=None):
        self.tool_registry = tool_registry
        self.execution_count = 0
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute an atomic task and return result."""
        self.execution_count += 1
        
        # For MVP: simple mock execution
        # In production: this would compile task to workflow, execute workflow, or call tools
        
        result = {
            'task_id': task.id,
            'output': f"Executed: {task.description}",
            'execution_count': self.execution_count,
            'inputs_received': task.inputs
        }
        
        # Simulate some processing
        time.sleep(0.01)
        
        return result


class TaskVerifier:
    """
    Verifies that task results meet specified criteria.
    Checks both explicit verification criteria and implicit correctness.
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.verification_count = 0
    
    def verify(self, task: Task) -> Dict[str, Any]:
        """ Verify task result against verification criteria."""
        self.verification_count += 1
        
        if task.result is None:
            return {
                'valid': False,
                'log': ['Task has no result'],
                'verification_id': self.verification_count
            }
        
        checks = []
        all_passed = True
        
        # Check explicit verification criteria
        for criterion in task.verification_criteria:
            # MVP: simple presence check
            passed = self._check_criterion(task.result, criterion)
            checks.append({
                'criterion': criterion,
                'passed': passed
            })
            if not passed:
                all_passed = False
        
        # If no explicit criteria, do basic sanity check
        if not task.verification_criteria:
            checks.append({
                'criterion': 'Result exists and is not empty',
                'passed': True
            })
        
        return {
            'valid': all_passed,
            'log': [f"{c['criterion']}: {'PASS' if c['passed'] else 'FAIL'}" for c in checks],
            'verification_id': self.verification_count
        }
    
    def _check_criterion(self, result: Dict[str, Any], criterion: str) -> bool:
        """Check if result satisfies a single criterion."""
        # MVP: simple keyword check
        # Production: could use LLM or formal verification
        
        if 'output' in result and criterion.lower() in str(result['output']).lower():
            return True
        
        return True  # Default to pass for MVP


class ResultCombiner:
    """
    Combines results from sub-tasks into a final result.
    Follows the recombination plan from decomposition.
    """
    
    def __init__(self):
        self.combination_count = 0
    
    def combine(self, task: Task, sub_tasks: List[Task], 
                sub_results: List[Dict[str, Any]], recombination_plan: str) -> Dict[str, Any]:
        """Combine sub-task results according to recombination plan."""
        self.combination_count += 1
        
        if not sub_results:
            return {'error': 'No sub-results to combine'}
        
        if recombination_plan.startswith("Chain"):
            # Sequential: last result is final
            return sub_results[-1]['result']
        
        elif recombination_plan.startswith("Merge"):
            # Parallel: merge all results
            combined = {
                'combined_from': [r['result'].get('task_id', '') for r in sub_results],
                'outputs': [r['result'].get('output', '') for r in sub_results],
                'all_verified': all(r['verified'] for r in sub_results)
            }
            return combined
        
        else:
            # Direct: return first/only result
            return sub_results[0]['result']
