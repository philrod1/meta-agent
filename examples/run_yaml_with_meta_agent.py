"""Example: load a high-level YAML workflow and run it through MetaAgent
using the YAML-aware decomposer loader implemented in `src/workflow/loader.py`.

This demonstrates Option A: interpret the LLM-produced YAML using the
MetaAgent machinery (choice handling already implemented in MetaAgent).
"""
from src.workflow.loader import load_yaml_to_meta_agent
from src.meta_agent import MetaAgent, TaskExecutor
from src.workflow.factory import get_agent_creation_count, reset_agent_creation_count
import collections


class DemoExecutor:
    """Executor with lightweight, problem-specific behaviors for the sorting demo.

    This executor is created in the example (not in meta_agent) so the core remains
    task-agnostic. It recognizes common task ids/descriptions used in the YAML plan
    and returns structured outputs the combiner/verifier expect.
    """
    def __init__(self):
        self.count = 0

    def execute(self, task):
        self.count += 1
        inputs = getattr(task, 'inputs', {}) or {}
        desc = (getattr(task, 'description', '') or '').lower()
        tid = getattr(task, 'id', '').lower()
        print(f"[DEMO EXEC] task={getattr(task,'id',None)} inputs={inputs}")

        # If the task has a 'numbers' input, produce a sorted list (demo shortcut).
        # In a real system, nested workflow calls would be resolved and executed.
        # if 'numbers' in inputs and isinstance(inputs['numbers'], list):
        #     nums = inputs['numbers']
        #     return {'sorted_numbers': sorted(nums)}

        # Split behavior
        if 'numbers' in inputs and ('split' in tid or 'split' in desc):
            nums = inputs['numbers'] or []
            mid = len(nums) // 2
            return {'left': nums[:mid], 'right': nums[mid:]}

        # Merge behavior
        if 'left_sorted' in inputs and 'right_sorted' in inputs:
            left = inputs.get('left_sorted') or []
            right = inputs.get('right_sorted') or []
            merged = []
            i = j = 0
            while i < len(left) and j < len(right):
                if left[i] <= right[j]:
                    merged.append(left[i]); i += 1
                else:
                    merged.append(right[j]); j += 1
            merged.extend(left[i:]); merged.extend(right[j:])
            return {'sorted_numbers': merged}

        # Fallback
        return {'output': f'Executed: {task.description}'}


def main():
    root_task, decomposer, verifier, combiner = load_yaml_to_meta_agent('specs/yaml/sorting.yaml')

    # Use the generic TaskExecutor which will call registered tools from the tools registry
    executor = TaskExecutor()

    # reset agent creation count for clear measurement
    reset_agent_creation_count()

    meta_agent = MetaAgent(decomposer=decomposer, executor=executor, verifier=verifier, combiner=combiner)

    # Example inputs: test a short list to trigger the 'choice' branch
    #root_task.inputs = {'numbers': [2, 1]}

    # Example inputs: test a longer list to trigger recursive splitting/merging
    root_task.inputs = {'numbers': [5, 3, 8, 1, 4, 7, 6, 2]}

    # A truly ridiculous list to sort, generated randomly
    # import random
    # random_list = random.sample(range(1, 50000000), 20000)
    # root_task.inputs = {'numbers': random_list}

    print('Input list to sort:', root_task.inputs['numbers'])

    result = meta_agent.solve(root_task)

    # Extract sorted list (try several places depending on how task results are shaped)
    sorted_list = None
    # 1) Top-level result dict
    top_result = result.get('result')
    if isinstance(top_result, dict) and 'sorted_numbers' in top_result:
        sorted_list = top_result['sorted_numbers']

    # 2) execution_tree.result (task.result may be a dict with 'sorted_numbers')
    if sorted_list is None:
        exec_tree = result.get('execution_tree')
        if exec_tree and getattr(exec_tree, 'result', None):
            r = getattr(exec_tree, 'result')
            if isinstance(r, dict) and 'sorted_numbers' in r:
                sorted_list = r['sorted_numbers']

    # 3) nested outputs returned by the combiner may use other shapes; fall back to printing whole result
    print('\n--- RUN RESULT ---')
    print('verified:', result.get('verified'))
    print('sorted_numbers:', sorted_list if sorted_list is not None else result.get('result'))

    # Report number of agents created during execution
    print('agents_created:', get_agent_creation_count())


if __name__ == '__main__':
    main()
