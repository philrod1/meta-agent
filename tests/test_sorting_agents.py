import pytest

from src.tools.registry import split_in_half, compare_and_return, join_two_sorted_lists
from src.workflow.loader import load_yaml_to_meta_agent
from src.meta_agent import MetaAgent, TaskExecutor
from src.workflow.factory import reset_agent_creation_count, get_agent_creation_count


def extract_sorted(result):
    # Try common locations for sorted list
    if not result:
        return None
    if isinstance(result, dict):
        if 'sorted_numbers' in result:
            return result['sorted_numbers']
        # result might be nested as {'result': {...}}
        if 'result' in result and isinstance(result['result'], dict) and 'sorted_numbers' in result['result']:
            return result['result']['sorted_numbers']
    return None


def test_split_in_half_basic():
    out = split_in_half([1, 2, 3, 4])
    assert out == {'left': [1, 2], 'right': [3, 4]}


def test_compare_and_return_basic():
    out = compare_and_return([2, 1])
    assert out == {'sorted_numbers': [1, 2]}


def test_join_two_sorted_lists_basic():
    out = join_two_sorted_lists([1, 2], [3, 4])
    assert out == {'sorted_numbers': [1, 2, 3, 4]}


def test_meta_agent_sorts_len2():
    root, decomposer, verifier, combiner = load_yaml_to_meta_agent('specs/yaml/sorting.yaml')
    reset_agent_creation_count()
    executor = TaskExecutor()
    meta = MetaAgent(decomposer=decomposer, executor=executor, verifier=verifier, combiner=combiner)

    root.inputs = {'numbers': [2, 1]}
    res = meta.solve(root)

    assert res['verified'] is True
    sorted_list = extract_sorted(res.get('result'))
    # combiner may place result at top-level or nested; also try execution_tree
    if sorted_list is None:
        et = res.get('execution_tree')
        if et and getattr(et, 'result', None):
            sorted_list = et.result.get('sorted_numbers')

    assert sorted_list == [1, 2]
    assert get_agent_creation_count() >= 1


def test_meta_agent_sorts_len3():
    root, decomposer, verifier, combiner = load_yaml_to_meta_agent('specs/yaml/sorting.yaml')
    reset_agent_creation_count()
    executor = TaskExecutor()
    meta = MetaAgent(decomposer=decomposer, executor=executor, verifier=verifier, combiner=combiner)

    root.inputs = {'numbers': [3, 1, 2]}
    res = meta.solve(root)

    assert res['verified'] is True
    sorted_list = extract_sorted(res.get('result'))
    if sorted_list is None:
        et = res.get('execution_tree')
        if et and getattr(et, 'result', None):
            sorted_list = et.result.get('sorted_numbers')

    assert sorted_list == [1, 2, 3]
    # expect multiple atomic executions for split/compare/merge
    assert get_agent_creation_count() >= 2


def test_meta_agent_sorts_len8_agent_count():
    """Run the 8-element sorting workflow and assert atomic agent count is within expected bound."""
    root, decomposer, verifier, combiner = load_yaml_to_meta_agent('specs/yaml/sorting.yaml')
    reset_agent_creation_count()
    executor = TaskExecutor()
    meta = MetaAgent(decomposer=decomposer, executor=executor, verifier=verifier, combiner=combiner)

    root.inputs = {'numbers': [8, 7, 6, 5, 4, 3, 2, 1]}
    res = meta.solve(root)

    assert res['verified'] is True
    sorted_list = extract_sorted(res.get('result'))
    if sorted_list is None:
        et = res.get('execution_tree')
        if et and getattr(et, 'result', None):
            sorted_list = et.result.get('sorted_numbers')

    assert sorted_list == [1, 2, 3, 4, 5, 6, 7, 8]
    # For divide-and-conquer merge sort, 8 elements should need at most 15 atomic actions
    assert get_agent_creation_count() <= 15, f"Too many atomic agents: {get_agent_creation_count()}"
