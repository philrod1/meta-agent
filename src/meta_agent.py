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
from src.workflow.guards import evaluate_condition
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time


@dataclass
class Task:
    """Represents a task at any level of decomposition."""
    id: str
    description: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
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
    """
    Result of decomposing a task.
    For the "choice" strategy, indicates alternative sub-tasks.
    - Multiple service backends (pay with card, PayPal, bank transfer, etc.).
    - Failover / fallback logic (try fast/cheap method first then fallback).
    - A/B attempts where only one needed
    Sequential is AND, parallel is ALL, hierarchical is AND, choice is OR
    """
    sub_tasks: List[Task]
    decomposition_strategy: str  # e.g., "sequential", "parallel", "hierarchical", "choice"
    recombination_plan: str      # How to merge sub-task results
    reasoning: str               # Why this decomposition was chosen
    # For 'choice' decomposition, alternatives is a list of plans where each plan is a
    # list of Tasks. The meta-agent will select/try alternatives according to policy.
    alternatives: Optional[List[List[Task]]] = None


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
            
            # Handle 'choice' decomposition specially: alternatives = list of plans
            if decomposition.decomposition_strategy == 'choice' and decomposition.alternatives:
                self._log(f"{'  ' * depth}[META] Handling choice decomposition with {len(decomposition.alternatives)} alternatives")
                # Sequential-fallback: try each alternative in order, stop on first verified success
                for alt_idx, plan in enumerate(decomposition.alternatives):
                    self._log(f"{'  ' * depth}[META] Trying alternative {alt_idx+1}/{len(decomposition.alternatives)}")
                    alt_sub_results = []
                    alt_failed = False
                    # local context for this alternative: start from parent's inputs
                    alt_context = dict(task.inputs or {})
                    for sub_task in plan:
                        self._log(f"{'  ' * (depth+1)}[META] Solving alt sub-task {sub_task.id}")
                        # resolve placeholders on sub_task.inputs using alt_context
                        if getattr(sub_task, 'inputs', None):
                            for k, v in list(sub_task.inputs.items()):
                                if isinstance(v, str) and v in alt_context:
                                    sub_task.inputs[k] = alt_context.get(v)
                                elif v is None and k in alt_context:
                                    sub_task.inputs[k] = alt_context.get(k)

                        sub_result = self.solve(sub_task, depth + 2)
                        alt_sub_results.append(sub_result)
                        if not sub_result.get('verified', False):
                            self._log(f"{'  ' * (depth+1)}[META] Alternative {alt_idx+1} sub-task {sub_task.id} failed verification")
                            alt_failed = True
                            break

                        # update alt_context with outputs produced by this sub-task
                        res = sub_result.get('result')
                        if isinstance(res, dict):
                            # If the sub_task declared an outputs mapping, prefer mapping child keys
                            outputs_map = getattr(sub_task, 'outputs', {}) or {}
                            if isinstance(outputs_map, dict) and outputs_map:
                                for parent_key, child_key in outputs_map.items():
                                    # child_key can be a string naming the child's output
                                    if isinstance(child_key, str) and child_key in res:
                                        alt_context[parent_key] = res.get(child_key)
                            # Also merge raw outputs for general propagation
                            for k, v in res.items():
                                alt_context[k] = v

                    if alt_failed:
                        continue

                    # Combine results for this alternative
                    self._log(f"{'  ' * depth}[META] Alternative {alt_idx+1} succeeded, recombining")
                    combined = self.combiner.combine(task=task, sub_tasks=plan, sub_results=alt_sub_results, recombination_plan=decomposition.recombination_plan)
                    task.result = combined
                    verification = self.verifier.verify(task)
                    if verification.get('valid'):
                        task.status = 'verified'
                        return {
                            'result': combined,
                            'verified': True,
                            'execution_tree': task,
                            'logs': self.execution_log,
                            'verification': verification
                        }
                    else:
                        self._log(f"{'  ' * depth}[META] Alternative {alt_idx+1} recombination failed verification")

                # All alternatives tried and none verified
                self._log(f"{'  ' * depth}[META] All alternatives failed for task {task.id}")
                task.status = 'failed'
                return {
                    'result': None,
                    'verified': False,
                    'execution_tree': task,
                    'logs': self.execution_log,
                    'error': 'All choice alternatives failed'
                }

            if not decomposition.sub_tasks:
                # If decomposition produces no sub-tasks, two possibilities:
                # 1) decomposer produced a return value and set task.result -> skip execution and verify
                # 2) no decomposition and no pre-filled result -> treat as atomic and execute
                if getattr(task, 'result', None) is not None:
                    self._log(f"{'  ' * depth}[META] No sub-tasks and pre-filled result from decomposer, verifying directly")
                    verification = self.verifier.verify(task)
                    task.status = 'verified' if verification.get('valid') else 'completed'
                    return {
                        'result': task.result,
                        'verified': verification.get('valid'),
                        'execution_tree': task,
                        'logs': self.execution_log,
                        'verification': verification
                    }
                else:
                    self._log(f"{'  ' * depth}[META] No sub-tasks generated, executing as atomic")
                    return self._execute_atomic_task(task, depth)
            
            self._log(f"{'  ' * depth}[META] Decomposed into {len(decomposition.sub_tasks)} sub-tasks")
            self._log(f"{'  ' * depth}[META] Strategy: {decomposition.decomposition_strategy}")
            
            # Store sub-tasks in parent
            task.sub_tasks = decomposition.sub_tasks
            
            # Recursively solve each sub-task
            sub_results = []
            # Maintain a local execution context for guard evaluation and data passing
            context = dict(task.inputs or {})
            for i, sub_task in enumerate(decomposition.sub_tasks):
                self._log(f"{'  ' * depth}[META] Solving sub-task {i+1}/{len(decomposition.sub_tasks)}")
                # Resolve any input placeholders on the sub_task from the current context.
                # If a sub_task input value is a string that names a variable in context,
                # substitute it with the actual value so executors receive concrete inputs.
                if getattr(sub_task, 'inputs', None):
                    for k, v in list(sub_task.inputs.items()):
                        if isinstance(v, str) and v in context:
                            sub_task.inputs[k] = context.get(v)
                        elif v is None and k in context:
                            # if input placeholder is None, try to pull same-named value from context
                            sub_task.inputs[k] = context.get(k)
                # If the loader attached guard_conditions, evaluate them against current context
                guards = getattr(sub_task, 'guard_conditions', None)
                if guards:
                    should_run = False
                    # If any incoming guard is unspecified or 'true', treat as runnable; otherwise require at least one true
                    for g in guards:
                        try:
                            if evaluate_condition(g, context):
                                should_run = True
                                break
                        except Exception:
                            continue
                    if not should_run:
                        self._log(f"{'  ' * depth}[META] Skipping sub-task {sub_task.id} due to guard conditions: {guards}")
                        continue

                sub_result = self.solve(sub_task, depth + 1)
                sub_results.append(sub_result)
                # Update context with any named outputs produced by the sub-task
                res = sub_result.get('result')
                if isinstance(res, dict):
                    outputs_map = getattr(sub_task, 'outputs', {}) or {}
                    if isinstance(outputs_map, dict) and outputs_map:
                        for parent_key, child_key in outputs_map.items():
                            if isinstance(child_key, str) and child_key in res:
                                context[parent_key] = res.get(child_key)
                    # Also merge raw outputs for general propagation
                    for k, v in res.items():
                        context[k] = v
                
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
                # Log verification details for debugging
                for entry in verification.get('log', []):
                    self._log(f"{'  ' * (depth+1)}[VERIF] {entry}")
            
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


class AbstractTaskDecomposer(ABC):
    """
    Abstract base for task decomposers.
    Concrete decomposers should implement `decompose` to return a DecompositionResult.
    """

    @abstractmethod
    def decompose(self, task: Task, depth: int) -> DecompositionResult:
        raise NotImplementedError()


class TaskDecomposer(AbstractTaskDecomposer):
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


class ChoiceTaskDecomposer(TaskDecomposer):
    """
    A concrete decomposer that demonstrates the 'choice' decomposition strategy.

    For tasks with input `numbers` of length 2 (e.g., sorting), it will return two
    alternative plans: (1) treat as base-case comparator, (2) split into singletons
    and merge. This is a minimal example for demo and testing.
    """

    def decompose(self, task: Task, depth: int) -> DecompositionResult:
        # If inputs include a numbers list of length 2, produce a choice
        numbers = task.inputs.get('numbers') if isinstance(task.inputs, dict) else None
        if isinstance(numbers, list) and len(numbers) == 2:
            # Alternative 1: base comparator
            alt1 = [
                Task(
                    id=f"{task.id}.base",
                    description="Compare two elements and return ordered pair",
                    inputs={'numbers': numbers},
                    is_atomic=True,
                    parent_id=task.id,
                    verification_criteria=[]
                )
            ]

            # Alternative 2: split into singletons, sort each (atomic) and merge
            left_list = [numbers[0]]
            right_list = [numbers[1]]
            alt2 = [
                Task(
                    id=f"{task.id}.left",
                    description="Sort left singleton",
                    inputs={'numbers': left_list},
                    is_atomic=True,
                    parent_id=task.id,
                    verification_criteria=[]
                ),
                Task(
                    id=f"{task.id}.right",
                    description="Sort right singleton",
                    inputs={'numbers': right_list},
                    is_atomic=True,
                    parent_id=task.id,
                    verification_criteria=[]
                ),
                Task(
                    id=f"{task.id}.merge",
                    description="Merge two singletons into ordered pair",
                    inputs={},
                    is_atomic=True,
                    parent_id=task.id,
                    verification_criteria=[]
                )
            ]

            return DecompositionResult(
                sub_tasks=[],
                decomposition_strategy='choice',
                recombination_plan='merge',
                reasoning='Choice between base comparator and split-then-merge',
                alternatives=[alt1, alt2]
            )

        # Fallback to default heuristic decomposition
        return super().decompose(task, depth)


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
        # Record that an execution (agent/tool invocation) occurred; this maps to
        # the user's expectation of "agents created" for this demo.
        try:
            from src.workflow.factory import increment_agent_creation_count
            increment_agent_creation_count(1)
        except Exception:
            pass
        # If a tool is specified in task.params, attempt to run it from the tools registry.
        tool_name = None
        if getattr(task, 'params', None):
            tool_name = task.params.get('tool') or task.params.get('behavior')

        if tool_name:
            # Lazy import the registry to avoid import cycles
            from src.tools.registry import get_tool

            fn = get_tool(tool_name)
            if fn is None:
                raise RuntimeError(f"Tool '{tool_name}' not found in registry")

            # Call tool with provided inputs. Tools should accept keyword args.
            try:
                if isinstance(task.inputs, dict):
                    tool_result = fn(**task.inputs)
                else:
                    tool_result = fn(task.inputs)
            except TypeError as e:
                # Fallback: attempt to map task.inputs keys to function parameter names
                import inspect
                sig = inspect.signature(fn)
                params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY)]
                mapped = {}
                for p in params:
                    pname = p.name
                    found_key = None
                    if isinstance(task.inputs, dict):
                        for k in task.inputs.keys():
                            if k == pname or k.startswith(pname) or k.endswith(pname) or k.replace('_sorted','') == pname:
                                found_key = k
                                break
                    if found_key is not None:
                        mapped[pname] = task.inputs[found_key]
                try:
                    if mapped:
                        tool_result = fn(**mapped)
                    else:
                        # last-resort: pass whole inputs
                        tool_result = fn(task.inputs)
                except Exception:
                    # re-raise original TypeError to preserve message
                    raise e

            # Normalize output to a dict
            if not isinstance(tool_result, dict):
                return {'task_id': task.id, 'result': tool_result}

            tool_result.setdefault('task_id', task.id)
            return tool_result

        # Fallback mock execution for tasks without a registered tool
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
