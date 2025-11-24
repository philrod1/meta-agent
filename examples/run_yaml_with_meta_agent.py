"""Example: load a high-level YAML workflow and run it through MetaAgent
Demonstrates the chice handling capabilities of MetaAgent and scalability with large inputs.
"""
from src.workflow.loader import load_yaml_to_meta_agent
from src.meta_agent import MetaAgent, TaskExecutor
from src.workflow.factory import get_agent_creation_count, reset_agent_creation_count


def main():
    root_task, decomposer, verifier, combiner = load_yaml_to_meta_agent('specs/yaml/sorting.yaml')

    # Use the generic TaskExecutor which will call registered tools from the tools registry
    executor = TaskExecutor()

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
    sorted_list = None
    top_result = result.get('result')

    if isinstance(top_result, dict) and 'sorted_numbers' in top_result:
        sorted_list = top_result['sorted_numbers']

    if sorted_list is None:
        exec_tree = result.get('execution_tree')
        if exec_tree and getattr(exec_tree, 'result', None):
            r = getattr(exec_tree, 'result')
            if isinstance(r, dict) and 'sorted_numbers' in r:
                sorted_list = r['sorted_numbers']

    print('\n--- RUN RESULT ---')
    print('verified:', result.get('verified'))
    print('sorted_numbers:', sorted_list if sorted_list is not None else result.get('result'))
    print('agents_created:', get_agent_creation_count())


if __name__ == '__main__':
    main()
