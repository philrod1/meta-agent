"""Tests for workflow compiler (YAML loading and validation)."""

import pytest
from src.workflow.compiler import load_workflow
from src.workflow.models import Workflow, Node, Edge


def test_load_workflow_from_valid_yaml():
    """Test loading a valid workflow from YAML."""
    yaml_text = """
name: test_workflow
description: A test workflow
inputs: [input1, input2]
outputs: [output1]
preconditions: []
success_criteria: ["output1 != None"]
failure_conditions: []

nodes:
  - id: step1
    type: tool
    summary: First step
    params: { tool: "mock_tool" }
    io: { inputs: [input1], outputs: [result1] }
    tests: ["result1 != None"]
    
  - id: step2
    type: tool
    summary: Second step
    params: { tool: "another_tool" }
    io: { inputs: [result1], outputs: [output1] }
    tests: []

edges:
  - { from: step1, to: step2, when: "true" }
"""
    
    workflow = load_workflow(yaml_text)
    
    assert workflow.name == "test_workflow"
    assert workflow.description == "A test workflow"
    assert workflow.inputs == ["input1", "input2"]
    assert workflow.outputs == ["output1"]
    assert len(workflow.nodes) == 2
    assert len(workflow.edges) == 1
    assert workflow.nodes[0].id == "step1"
    assert workflow.nodes[1].id == "step2"


def test_load_workflow_missing_required_field():
    """Test that missing required fields raise ValueError."""
    yaml_text = """
name: incomplete_workflow
inputs: [input1]
# Missing: nodes, edges, success_criteria, failure_conditions
"""
    
    with pytest.raises(ValueError, match="Missing required top-level field"):
        load_workflow(yaml_text)


def test_validate_workflow_detects_cycle():
    """Test that cyclic workflows are rejected."""
    yaml_text = """
name: cyclic_workflow
inputs: [input1]
outputs: [output1]
success_criteria: []
failure_conditions: []

nodes:
  - id: step1
    type: tool
    params: { tool: "tool1" }
    io: { inputs: [input1], outputs: [result1] }
    
  - id: step2
    type: tool
    params: { tool: "tool2" }
    io: { inputs: [result1], outputs: [result2] }
    
  - id: step3
    type: tool
    params: { tool: "tool3" }
    io: { inputs: [result2], outputs: [output1] }

edges:
  - { from: step1, to: step2 }
  - { from: step2, to: step3 }
  - { from: step3, to: step1 }  # Creates a cycle!
"""
    
    with pytest.raises(ValueError, match="Cycle detected"):
        load_workflow(yaml_text)


def test_validate_workflow_detects_unknown_node_in_edge():
    """Test that edges referencing unknown nodes are rejected."""
    yaml_text = """
name: invalid_edge_workflow
inputs: [input1]
outputs: [output1]
success_criteria: []
failure_conditions: []

nodes:
  - id: step1
    type: tool
    params: { tool: "tool1" }
    io: { inputs: [input1], outputs: [result1] }

edges:
  - { from: step1, to: nonexistent_step }  # Unknown node!
"""
    
    with pytest.raises(ValueError, match="Edge references unknown node"):
        load_workflow(yaml_text)


def test_load_workflow_with_conditional_edges():
    """Test loading a workflow with conditional edges."""
    yaml_text = """
name: branching_workflow
inputs: [value]
outputs: [output]
success_criteria: []
failure_conditions: []

nodes:
  - id: check
    type: router
    params: {}
    io: { inputs: [value], outputs: [is_valid] }
    
  - id: process_valid
    type: tool
    params: { tool: "process" }
    io: { inputs: [value], outputs: [output] }
    
  - id: process_invalid
    type: tool
    params: { tool: "reject" }
    io: { inputs: [value], outputs: [output] }

edges:
  - { from: check, to: process_valid, when: "is_valid == true" }
  - { from: check, to: process_invalid, when: "is_valid == false" }
"""
    
    workflow = load_workflow(yaml_text)
    
    assert len(workflow.edges) == 2
    assert workflow.edges[0].when == "is_valid == true"
    assert workflow.edges[1].when == "is_valid == false"


def test_load_workflow_preserves_node_metadata():
    """Test that all node metadata is preserved during loading."""
    yaml_text = """
name: metadata_test
inputs: [x]
outputs: [y]
success_criteria: []
failure_conditions: []

nodes:
  - id: process
    type: tool
    summary: This processes the input
    params: { tool: "processor", mode: "fast" }
    io: { inputs: [x], outputs: [y] }
    tests: ["y > 0", "y != None"]

edges: []
"""
    
    workflow = load_workflow(yaml_text)
    node = workflow.nodes[0]
    
    assert node.id == "process"
    assert node.type == "tool"
    assert node.summary == "This processes the input"
    assert node.params == {"tool": "processor", "mode": "fast"}
    assert node.io_inputs == ["x"]
    assert node.io_outputs == ["y"]
    assert node.tests == ["y > 0", "y != None"]


def test_load_workflow_with_multiple_entry_points():
    """Test loading a DAG with multiple entry points (zero in-degree)."""
    yaml_text = """
name: multi_entry_workflow
inputs: [a, b]
outputs: [result]
success_criteria: []
failure_conditions: []

nodes:
  - id: process_a
    type: tool
    params: { tool: "tool_a" }
    io: { inputs: [a], outputs: [a_result] }
    
  - id: process_b
    type: tool
    params: { tool: "tool_b" }
    io: { inputs: [b], outputs: [b_result] }
    
  - id: combine
    type: tool
    params: { tool: "combiner" }
    io: { inputs: [a_result, b_result], outputs: [result] }

edges:
  - { from: process_a, to: combine }
  - { from: process_b, to: combine }
"""
    
    workflow = load_workflow(yaml_text)
    
    assert len(workflow.nodes) == 3
    assert len(workflow.edges) == 2
    # Both process_a and process_b should have in-degree 0
