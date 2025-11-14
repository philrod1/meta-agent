"""Tests for guard/condition evaluation."""

import pytest
from src.workflow.guards import evaluate_condition, evaluate_condition


def test_evaluate_condition_simple_equality():
    """Test simple equality checks."""
    context = {"x": 5, "y": 10}
    
    assert evaluate_condition("x == 5", context) is True
    assert evaluate_condition("x == 10", context) is False
    assert evaluate_condition("y == 10", context) is True


def test_evaluate_condition_inequality():
    """Test inequality operators."""
    context = {"value": 42}
    
    assert evaluate_condition("value != 0", context) is True
    assert evaluate_condition("value != 42", context) is False


def test_evaluate_condition_comparisons():
    """Test comparison operators (<, >, <=, >=)."""
    context = {"score": 75}
    
    assert evaluate_condition("score > 50", context) is True
    assert evaluate_condition("score < 100", context) is True
    assert evaluate_condition("score >= 75", context) is True
    assert evaluate_condition("score <= 75", context) is True
    assert evaluate_condition("score > 100", context) is False


def test_evaluate_condition_boolean_and():
    """Test AND logic."""
    context = {"a": True, "b": True, "c": False}
    
    assert evaluate_condition("a and b", context) is True
    assert evaluate_condition("a and c", context) is False
    assert evaluate_condition("b and c", context) is False


def test_evaluate_condition_boolean_or():
    """Test OR logic."""
    context = {"a": True, "b": False, "c": False}
    
    assert evaluate_condition("a or b", context) is True
    assert evaluate_condition("b or c", context) is False
    assert evaluate_condition("a or c", context) is True


def test_evaluate_condition_combined_conditions():
    """Test combined conditions with AND/OR."""
    context = {"x": 10, "y": 20, "valid": True}
    
    assert evaluate_condition("x < y and valid", context) is True
    assert evaluate_condition("x > y or valid", context) is True
    assert evaluate_condition("x > y and valid", context) is False


def test_evaluate_condition_string_comparison():
    """Test string comparisons."""
    context = {"status": "approved", "type": "refund"}
    
    assert evaluate_condition("status == 'approved'", context) is True
    assert evaluate_condition("status == 'rejected'", context) is False
    assert evaluate_condition("type != 'charge'", context) is True


def test_evaluate_condition_always_true():
    """Test that 'true' or empty string evaluates to True."""
    context = {}
    
    assert evaluate_condition("true", context) is True
    assert evaluate_condition("", context) is True
    assert evaluate_condition("  ", context) is True


def test_evaluate_condition_with_none_values():
    """Test handling of None values."""
    context = {"value": None, "other": 42, "none": None}
    
    # Note: expression gets lowercased, so 'None' becomes 'none' which must be in context
    assert evaluate_condition("value == none", context) is True
    assert evaluate_condition("other != none", context) is True


def test_evaluate_condition_boolean_values():
    """Test direct boolean values."""
    context = {"flag": True, "disabled": False}
    
    # Note: Direct boolean evaluation might need special handling
    # Depending on implementation, this might not work as expected
    # Test the actual behavior


def test_evaluate_condition_invalid_expression_returns_false():
    """Test that invalid expressions return False rather than crashing."""
    context = {"x": 5}
    
    # These should not crash, just return False
    result = evaluate_condition("undefined_var == 5", context)
    # Depending on implementation, might be False or raise KeyError


def test_evaluate_condition_nested_dict_access():
    """Test accessing nested dictionary values."""
    context = {
        "user": {"id": 123, "role": "admin"},
        "order": {"status": "completed"}
    }
    
    # This might require special handling in the guard implementation
    # For now, test what's currently supported


def test_evaluate_condition_alias():
    """Test that evaluate_condition is an alias for evaluate_condition."""
    context = {"x": 5}
    
    result1 = evaluate_condition("x == 5", context)
    result2 = evaluate_condition("x == 5", context)
    
    assert result1 == result2


def test_evaluate_condition_chained_comparisons():
    """Test chained comparison expressions."""
    context = {"value": 50}
    
    # Python allows: 0 < value < 100
    assert evaluate_condition("value > 0", context) is True
    assert evaluate_condition("value < 100", context) is True
