"""Tests for agent implementations."""

import pytest
from src.agents.base import BaseAgent
from src.agents.tool import ToolAgent
from src.agents.router import RouterAgent
from src.agents.approval import ApprovalAgent
from src.tools.registry import register_tool


# Register a simple test tool
@register_tool("test.increment")
def tool_increment(value: int) -> dict:
    """Test tool that increments a value."""
    return {"incremented": value + 1}


def test_base_agent_is_abstract():
    """Test that BaseAgent cannot be instantiated directly."""
    # BaseAgent is abstract and requires execute() implementation
    with pytest.raises(TypeError):
        BaseAgent("test_id", {}, [], [])


def test_tool_agent_execute():
    """Test ToolAgent execution with a registered tool."""
    agent = ToolAgent(
        node_id="test_node",
        params={"tool": "test.increment"},
        inputs=["value"],
        outputs=["incremented"]
    )
    
    context = {"value": 5}
    result = agent.execute(context)
    
    assert "incremented" in result
    assert result["incremented"] == 6


def test_tool_agent_missing_tool_parameter():
    """Test that ToolAgent raises error when 'tool' parameter is missing."""
    agent = ToolAgent(
        node_id="test_node",
        params={},  # Missing 'tool' parameter
        inputs=["value"],
        outputs=["result"]
    )
    
    context = {"value": 5}
    
    with pytest.raises(ValueError, match="missing 'tool' parameter"):
        agent.execute(context)


def test_tool_agent_unknown_tool():
    """Test that ToolAgent raises error for unknown tools."""
    agent = ToolAgent(
        node_id="test_node",
        params={"tool": "nonexistent.tool"},
        inputs=["value"],
        outputs=["result"]
    )
    
    context = {"value": 5}
    
    with pytest.raises(ValueError, match="Tool not found"):
        agent.execute(context)


def test_tool_agent_dry_run():
    """Test ToolAgent dry-run mode."""
    agent = ToolAgent(
        node_id="test_node",
        params={"tool": "test.increment"},
        inputs=["value"],
        outputs=["incremented"]
    )
    
    context = {"value": 5}
    result = agent.dry_run(context)
    
    # Dry run should return placeholder values
    assert "incremented" in result
    assert isinstance(result["incremented"], str)
    assert "test_node:incremented:DRY" == result["incremented"]


def test_tool_agent_with_missing_inputs():
    """Test ToolAgent behavior when context is missing expected inputs."""
    agent = ToolAgent(
        node_id="test_node",
        params={"tool": "test.increment"},
        inputs=["value", "other"],  # 'other' not in context
        outputs=["incremented"]
    )
    
    context = {"value": 5}
    result = agent.execute(context)
    
    # Should still execute with available inputs
    assert "incremented" in result


def test_router_agent_execute():
    """Test RouterAgent execution."""
    agent = RouterAgent(
        node_id="router",
        params={"task_type": "type_a"},
        inputs=["data"],
        outputs=["result"]
    )
    
    context = {"data": "test_data"}
    result = agent.execute(context)
    
    assert "result" in result
    assert "Agent A" in result["result"]


def test_router_agent_different_routes():
    """Test RouterAgent with different task types."""
    context = {"data": "test"}
    
    # Route to Agent A
    agent_a = RouterAgent("router", {"task_type": "type_a"}, ["data"], ["result"])
    result_a = agent_a.execute(context)
    assert "Agent A" in result_a["result"]
    
    # Route to Agent B
    agent_b = RouterAgent("router", {"task_type": "type_b"}, ["data"], ["result"])
    result_b = agent_b.execute(context)
    assert "Agent B" in result_b["result"]
    
    # No suitable agent
    agent_c = RouterAgent("router", {"task_type": "unknown"}, ["data"], ["result"])
    result_c = agent_c.execute(context)
    assert "No suitable agent" in result_c["result"]


def test_approval_agent_execute():
    """Test ApprovalAgent execution."""
    agent = ApprovalAgent(
        node_id="approval",
        params={"timeout_hours": 24},
        inputs=["request"],
        outputs=["approved"]
    )
    
    context = {"request": "refund request"}
    result = agent.execute(context)
    
    assert "approved" in result
    assert isinstance(result["approved"], bool)


def test_approval_agent_with_preapproved_context():
    """Test ApprovalAgent when approval status is in context."""
    agent = ApprovalAgent(
        node_id="approval",
        params={"timeout_hours": 24},
        inputs=["request"],
        outputs=["approved"]
    )
    
    # Test with pre-existing approval
    context = {"request": "refund", "approved": False}
    result = agent.execute(context)
    assert result["approved"] is False
    
    context = {"request": "refund", "approved": True}
    result = agent.execute(context)
    assert result["approved"] is True


def test_agent_plan_method():
    """Test that agents have a plan() method."""
    agent = ToolAgent(
        node_id="test",
        params={"tool": "test.increment"},
        inputs=["value"],
        outputs=["result"]
    )
    
    context = {"value": 5}
    plan = agent.plan(context)
    
    # Default implementation returns empty dict
    assert isinstance(plan, dict)


def test_agent_initialization():
    """Test agent initialization with all parameters."""
    agent = ToolAgent(
        node_id="test_id",
        params={"tool": "test.increment", "extra": "param"},
        inputs=["in1", "in2"],
        outputs=["out1", "out2"],
        tests=["out1 > 0", "out2 != None"]
    )
    
    assert agent.node_id == "test_id"
    assert agent.params == {"tool": "test.increment", "extra": "param"}
    assert agent.inputs == ["in1", "in2"]
    assert agent.outputs == ["out1", "out2"]
    assert agent.tests == ["out1 > 0", "out2 != None"]
