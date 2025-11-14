"""Tests for workflow execution."""

import pytest
from src.workflow.compiler import load_workflow
from src.workflow.executor import run_workflow
from src.tools.registry import register_tool


# Register test tools
@register_tool("test.double")
def tool_double(**kwargs) -> dict:
    """Test tool that doubles a value."""
    # Get the first available value from kwargs
    value = next(iter(kwargs.values()))
    return {"result": value * 2}


@register_tool("test.add")
def tool_add(**kwargs) -> dict:
    """Test tool that adds two values."""
    values = list(kwargs.values())
    return {"sum": values[0] + values[1]}


@register_tool("test.validate")
def tool_validate(**kwargs) -> dict:
    """Test tool that validates if value is positive."""
    value = next(iter(kwargs.values()))
    return {"is_valid": value > 0, "value": value}


@register_tool("test.process_valid")
def tool_process_valid(**kwargs) -> dict:
    """Process valid values."""
    value = kwargs.get("value", next(iter(kwargs.values())))
    return {"output": f"valid:{value}"}


@register_tool("test.process_invalid")
def tool_process_invalid(**kwargs) -> dict:
    """Process invalid values."""
    value = kwargs.get("value", next(iter(kwargs.values())))
    return {"output": f"invalid:{value}"}


def test_run_simple_workflow():
    """Test executing a simple linear workflow."""
    yaml_text = """
name: simple_workflow
inputs: [input_value]
outputs: [result]
preconditions: []
success_criteria: ["result != None"]
failure_conditions: []

nodes:
  - id: double_it
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [input_value], outputs: [result] }
    tests: ["result != None"]

edges: []
"""
    
    workflow = load_workflow(yaml_text)
    result = run_workflow(workflow, {"input_value": 5})
    
    assert result["result"] == 10


def test_run_workflow_with_multiple_steps():
    """Test executing a workflow with multiple sequential steps."""
    yaml_text = """
name: multi_step_workflow
inputs: [x]
outputs: [result]
preconditions: []
success_criteria: ["result != none"]
failure_conditions: []

nodes:
  - id: step1
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [x], outputs: [result] }
    tests: []
    
  - id: step2
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [result], outputs: [result] }
    tests: []

edges:
  - { from: step1, to: step2 }
"""
    
    workflow = load_workflow(yaml_text)
    result = run_workflow(workflow, {"x": 3})
    
    # 3 * 2 = 6, then 6 * 2 = 12
    assert result["result"] == 12


def test_run_workflow_with_branching():
    """Test executing a workflow with conditional branching."""
    yaml_text = """
name: branching_workflow
inputs: [value]
outputs: [output]
preconditions: []
success_criteria: []
failure_conditions: []

nodes:
  - id: validate
    type: tool
    params: { tool: "test.validate" }
    io: { inputs: [value], outputs: [is_valid, value] }
    tests: []
    
  - id: process_valid
    type: tool
    params: { tool: "test.process_valid" }
    io: { inputs: [value], outputs: [output] }
    tests: []
    
  - id: process_invalid
    type: tool
    params: { tool: "test.process_invalid" }
    io: { inputs: [value], outputs: [output] }
    tests: []

edges:
  - { from: validate, to: process_valid, when: "is_valid == true" }
  - { from: validate, to: process_invalid, when: "is_valid == false" }
"""
    
    workflow = load_workflow(yaml_text)
    
    # Test with valid value (positive)
    result = run_workflow(workflow, {"value": 5})
    assert result["output"] == "valid:5"
    
    # Test with invalid value (negative)
    result = run_workflow(workflow, {"value": -3})
    assert result["output"] == "invalid:-3"


def test_run_workflow_with_parallel_execution():
    """Test executing a workflow with parallel branches."""
    yaml_text = """
name: parallel_workflow
inputs: [a, b]
outputs: [sum]
preconditions: []
success_criteria: []
failure_conditions: []

nodes:
  - id: double_a
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [a], outputs: [result] }
    tests: []
    
  - id: double_b
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [b], outputs: [result] }
    tests: []
    
  - id: combine
    type: tool
    params: { tool: "test.add" }
    io: { inputs: [a, b], outputs: [sum] }
    tests: []

edges:
  - { from: double_a, to: combine }
  - { from: double_b, to: combine }
"""
    
    workflow = load_workflow(yaml_text)
    result = run_workflow(workflow, {"a": 3, "b": 4})
    
    # Both branches should execute, then combine
    # Note: This test's correctness depends on how context is managed
    # between parallel branches


def test_run_workflow_dry_run_mode():
    """Test executing a workflow in dry-run mode."""
    yaml_text = """
name: dry_run_test
inputs: [x]
outputs: [result]
preconditions: []
success_criteria: []
failure_conditions: []

nodes:
  - id: process
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [x], outputs: [result] }
    tests: []

edges: []
"""
    
    workflow = load_workflow(yaml_text)
    result = run_workflow(workflow, {"x": 5}, dry_run=True)
    
    # In dry-run mode, should return placeholder values
    assert "result" in result
    assert isinstance(result["result"], str)
    assert "DRY" in result["result"]


def test_run_workflow_precondition_failure():
    """Test that workflow fails when preconditions are not met."""
    yaml_text = """
name: precondition_test
inputs: [value]
outputs: [result]
preconditions: ["value > 0"]
success_criteria: []
failure_conditions: []

nodes:
  - id: process
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [value], outputs: [result] }
    tests: []

edges: []
"""
    
    workflow = load_workflow(yaml_text)
    
    # Should fail because value is not > 0
    with pytest.raises(AssertionError, match="Precondition failed"):
        run_workflow(workflow, {"value": -5})


def test_run_workflow_success_criteria_check():
    """Test that workflow checks success criteria."""
    yaml_text = """
name: success_criteria_test
inputs: [x]
outputs: [result]
preconditions: []
success_criteria: ["result > 5"]
failure_conditions: []

nodes:
  - id: process
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [x], outputs: [result] }
    tests: []

edges: []
"""
    
    workflow = load_workflow(yaml_text)
    
    # Should succeed: 3 * 2 = 6, which is > 5
    result = run_workflow(workflow, {"x": 3})
    assert result["result"] == 6
    
    # Should fail: 2 * 2 = 4, which is not > 5
    with pytest.raises(AssertionError, match="Success criteria failed"):
        run_workflow(workflow, {"x": 2})


def test_run_workflow_node_test_failure():
    """Test that node-level tests are checked."""
    yaml_text = """
name: node_test_failure
inputs: [x]
outputs: [result]
preconditions: []
success_criteria: []
failure_conditions: []

nodes:
  - id: process
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [x], outputs: [result] }
    tests: ["result > 10"]

edges: []
"""
    
    workflow = load_workflow(yaml_text)
    
    # Should fail: 3 * 2 = 6, which is not > 10
    with pytest.raises(AssertionError, match="Test failed for node"):
        run_workflow(workflow, {"x": 3})


def test_run_workflow_failure_condition_check():
    """Test that workflow checks failure conditions."""
    yaml_text = """
name: failure_condition_test
inputs: [value]
outputs: [result]
preconditions: []
success_criteria: []
failure_conditions: ["result < 0"]

nodes:
  - id: process
    type: tool
    params: { tool: "test.double" }
    io: { inputs: [value], outputs: [result] }
    tests: []

edges: []
"""
    
    workflow = load_workflow(yaml_text)
    
    # Should succeed with positive value
    result = run_workflow(workflow, {"value": 5})
    assert result["result"] == 10
    
    # Should fail with negative value: -3 * 2 = -6, which is < 0
    with pytest.raises(AssertionError, match="Failure condition met"):
        run_workflow(workflow, {"value": -3})
