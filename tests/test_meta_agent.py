"""Tests for meta-agent orchestration."""

import pytest
from src.meta_agent import (
    Task, MetaAgent, TaskDecomposer, TaskExecutor, 
    TaskVerifier, ResultCombiner, DecompositionResult
)


def test_task_creation():
    """Test basic task creation."""
    task = Task(
        id="test-1",
        description="Test task",
        inputs={"key": "value"},
        is_atomic=False,
        verification_criteria=["criterion1"]
    )
    
    assert task.id == "test-1"
    assert task.description == "Test task"
    assert task.status == "pending"
    assert task.result is None
    assert len(task.sub_tasks) == 0


def test_task_decomposer_simple_task():
    """Test that simple tasks are not decomposed."""
    decomposer = TaskDecomposer()
    
    task = Task(
        id="simple-1",
        description="Calculate sum of numbers",
        is_atomic=True
    )
    
    result = decomposer.decompose(task, depth=0)
    
    assert result.decomposition_strategy == "none"
    assert len(result.sub_tasks) == 0


def test_task_decomposer_conjunction():
    """Test decomposition of tasks with 'and' conjunctions."""
    decomposer = TaskDecomposer()
    
    task = Task(
        id="conj-1",
        description="Fetch user data and validate email and check permissions",
        is_atomic=False
    )
    
    result = decomposer.decompose(task, depth=0)
    
    assert len(result.sub_tasks) == 3
    assert result.decomposition_strategy == "sequential"
    assert "Fetch user data" in result.sub_tasks[0].description
    assert all(st.parent_id == "conj-1" for st in result.sub_tasks)


def test_task_decomposer_sequential():
    """Test decomposition of sequential tasks with 'then'."""
    decomposer = TaskDecomposer()
    
    task = Task(
        id="seq-1",
        description="Load data then process data then save results",
        is_atomic=False
    )
    
    result = decomposer.decompose(task, depth=0)
    
    assert len(result.sub_tasks) == 3
    assert result.decomposition_strategy == "sequential"
    assert "Chain" in result.recombination_plan


def test_task_executor_basic():
    """Test basic task execution."""
    executor = TaskExecutor()
    
    task = Task(
        id="exec-1",
        description="Execute simple task",
        inputs={"value": 42}
    )
    
    result = executor.execute(task)
    
    assert result is not None
    assert "task_id" in result
    assert result["task_id"] == "exec-1"
    assert executor.execution_count == 1


def test_task_verifier_with_criteria():
    """Test verification with explicit criteria."""
    verifier = TaskVerifier()
    
    task = Task(
        id="verify-1",
        description="Test task",
        verification_criteria=["output", "success"],
        result={"output": "Task completed successfully", "data": [1, 2, 3]}
    )
    
    verification = verifier.verify(task)
    
    assert "valid" in verification
    assert "log" in verification
    assert len(verification["log"]) >= len(task.verification_criteria)


def test_task_verifier_no_result():
    """Test verification fails when task has no result."""
    verifier = TaskVerifier()
    
    task = Task(
        id="verify-2",
        description="Test task",
        result=None
    )
    
    verification = verifier.verify(task)
    
    assert verification["valid"] is False
    assert "no result" in verification["log"][0].lower()


def test_result_combiner_chain():
    """Test combining results with chain strategy."""
    combiner = ResultCombiner()
    
    parent_task = Task(id="parent", description="Parent task")
    sub_tasks = [
        Task(id="sub1", description="First"),
        Task(id="sub2", description="Second"),
    ]
    
    sub_results = [
        {"result": {"output": "Result 1"}, "verified": True},
        {"result": {"output": "Result 2"}, "verified": True},
    ]
    
    combined = combiner.combine(
        task=parent_task,
        sub_tasks=sub_tasks,
        sub_results=sub_results,
        recombination_plan="Chain: sequential results"
    )
    
    # Chain strategy should return last result
    assert combined["output"] == "Result 2"


def test_result_combiner_merge():
    """Test combining results with merge strategy."""
    combiner = ResultCombiner()
    
    parent_task = Task(id="parent", description="Parent task")
    sub_tasks = [
        Task(id="sub1", description="First"),
        Task(id="sub2", description="Second"),
    ]
    
    sub_results = [
        {"result": {"output": "Result 1"}, "verified": True},
        {"result": {"output": "Result 2"}, "verified": True},
    ]
    
    combined = combiner.combine(
        task=parent_task,
        sub_tasks=sub_tasks,
        sub_results=sub_results,
        recombination_plan="Merge: parallel results"
    )
    
    # Merge strategy should combine all outputs
    assert "outputs" in combined
    assert len(combined["outputs"]) == 2


def test_meta_agent_atomic_task():
    """Test meta-agent executing an atomic task."""
    decomposer = TaskDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    meta_agent = MetaAgent(decomposer, executor, verifier, combiner)
    
    task = Task(
        id="atomic-1",
        description="Simple atomic task",
        is_atomic=True,
        inputs={"value": 10}
    )
    
    result = meta_agent.solve(task)
    
    assert result is not None
    assert "result" in result
    assert "verified" in result
    assert "execution_tree" in result
    assert task.status in ["completed", "verified"]


def test_meta_agent_decomposable_task():
    """Test meta-agent with a task that gets decomposed."""
    decomposer = TaskDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    meta_agent = MetaAgent(decomposer, executor, verifier, combiner, max_depth=3)
    
    task = Task(
        id="decomp-1",
        description="Fetch data and process data and save results",
        is_atomic=False,
        inputs={"source": "database"}
    )
    
    result = meta_agent.solve(task)
    
    assert result is not None
    assert "result" in result
    assert "execution_tree" in result
    
    # Check that task was decomposed
    execution_tree = result["execution_tree"]
    assert len(execution_tree.sub_tasks) > 0


def test_meta_agent_max_depth():
    """Test that meta-agent respects max depth."""
    decomposer = TaskDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    # Set max_depth to 0 to force immediate execution
    meta_agent = MetaAgent(decomposer, executor, verifier, combiner, max_depth=0)
    
    task = Task(
        id="depth-1",
        description="Complex task and another task and yet another",
        is_atomic=False
    )
    
    result = meta_agent.solve(task)
    
    # Should be executed as atomic due to max_depth
    assert result is not None
    assert len(meta_agent.execution_log) > 0


def test_meta_agent_logging():
    """Test that meta-agent logs execution steps."""
    decomposer = TaskDecomposer()
    executor = TaskExecutor()
    verifier = TaskVerifier()
    combiner = ResultCombiner()
    
    meta_agent = MetaAgent(decomposer, executor, verifier, combiner)
    
    task = Task(
        id="log-1",
        description="Task with logging",
        is_atomic=True
    )
    
    result = meta_agent.solve(task)
    
    assert len(meta_agent.execution_log) > 0
    assert all("timestamp" in entry for entry in meta_agent.execution_log)
    assert all("message" in entry for entry in meta_agent.execution_log)


def test_decomposition_result_structure():
    """Test DecompositionResult structure."""
    sub_tasks = [
        Task(id="sub1", description="First sub-task"),
        Task(id="sub2", description="Second sub-task"),
    ]
    
    result = DecompositionResult(
        sub_tasks=sub_tasks,
        decomposition_strategy="parallel",
        recombination_plan="Merge all results",
        reasoning="Tasks are independent"
    )
    
    assert len(result.sub_tasks) == 2
    assert result.decomposition_strategy == "parallel"
    assert result.recombination_plan == "Merge all results"
    assert result.reasoning == "Tasks are independent"


def test_task_hierarchy():
    """Test parent-child task relationships."""
    parent = Task(id="parent", description="Parent task")
    
    child1 = Task(id="child1", description="Child 1", parent_id="parent")
    child2 = Task(id="child2", description="Child 2", parent_id="parent")
    
    parent.sub_tasks = [child1, child2]
    
    assert len(parent.sub_tasks) == 2
    assert child1.parent_id == "parent"
    assert child2.parent_id == "parent"
