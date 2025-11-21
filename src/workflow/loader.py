"""
Loader that converts a high-level, LLM-produced YAML (with decision/decomposition/choice)
into a Task + a YAML-aware decomposer that the MetaAgent can use directly.

This is a pragmatic, minimal implementation focused on the sorting example shape.
It is intended as Option A: interpret high-level YAML with MetaAgent rather than
translating to engine DAG.
"""
from typing import Any, Dict, List, Optional
import yaml
from ..meta_agent import Task, DecompositionResult, AbstractTaskDecomposer
from ..meta_agent import TaskVerifier, ResultCombiner
import collections


def _eval_simple_condition(cond: str, context: Dict[str, Any]) -> bool:
    """Evaluate a small set of guard expressions safely.

    Supports expressions like:
      - len(numbers) == N
      - len(numbers) > N
      - len(numbers) == 0/1
      - simple comparisons using the variable names in context
    Falls back to a restricted eval for simple expressions.
    """
    cond = cond.strip()
    # very small parser for common len(...) patterns
    if cond.startswith("len("):
        # allow forms like len(numbers) == 2 or len(numbers) > 2
        try:
            left, op, right = None, None, None
            if "==" in cond:
                left, right = cond.split("==")
                op = "=="
            elif ">=" in cond:
                left, right = cond.split(">=")
                op = ">="
            elif "<=" in cond:
                left, right = cond.split("<=")
                op = "<="
            elif ">" in cond:
                left, right = cond.split(">")
                op = ">"
            elif "<" in cond:
                left, right = cond.split("<")
                op = "<"
            else:
                return False
            left = left.strip()
            right = right.strip()
            # expect left like len(numbers)
            if left.startswith("len(") and left.endswith(")"):
                var = left[4:-1].strip()
                if var not in context:
                    return False
                # Only evaluate length checks for list-like objects. If the value is
                # a placeholder string (e.g. 'left' used to refer to another output),
                # treat the condition as unknown/false so we don't mis-evaluate it.
                actual = context.get(var)
                if not isinstance(actual, (list, tuple)):
                    return False
                val = len(actual)
                rval = int(right)
                if op == "==":
                    return val == rval
                if op == ">":
                    return val > rval
                if op == "<":
                    return val < rval
                if op == ">=":
                    return val >= rval
                if op == "<=":
                    return val <= rval
        except Exception:
            return False
    # fallback: try eval with restricted locals
    try:
        allowed_locals = {k: v for k, v in context.items()}
        # allow len builtin only
        allowed_builtins = {"len": len}
        return bool(eval(cond, {"__builtins__": allowed_builtins}, allowed_locals))
    except Exception:
        return False


class YamlTaskDecomposer(AbstractTaskDecomposer):
    """
    Decomposer that reads a parsed YAML high-level workflow spec and decomposes
    tasks according to the 'decision' node and its guards/decompositions.

    Very small, targeted implementation: looks for a single decision node and
    uses its guards to decide which decomposition to return.
    """

    def __init__(self, parsed_yaml: Dict[str, Any]):
        self.spec = parsed_yaml
        # find decision node if present (first node of type 'decision')
        self.decision_node = None
        for node in self.spec.get("nodes", []):
            if node.get("type") == "decision":
                self.decision_node = node
                break

    def decompose(self, task: Task, depth: int) -> DecompositionResult:
        # If no decision node, fallback to no decomposition
        if not self.decision_node:
            # If YAML looks like an engine-style spec (nodes + edges), map each node
            # to a sub-task and return a hierarchical decomposition. This enables
            # MetaAgent-driven lazy execution of engine-style workflows.
            if self.spec.get("nodes") and self.spec.get("edges") is not None:
                sub_tasks = self._nodes_to_tasks(self.spec.get("nodes", []), parent_id=task.id, root_inputs=task.inputs)
                return DecompositionResult(
                    sub_tasks=sub_tasks,
                    decomposition_strategy="hierarchical",
                    recombination_plan="merge",
                    reasoning="Mapped engine-style nodes into MetaAgent sub-tasks"
                )

            return DecompositionResult(
                sub_tasks=[],
                decomposition_strategy="none",
                recombination_plan="direct",
                reasoning="No decision node in YAML"
            )

        guards = self.decision_node.get("params", {}).get("guards", [])
        # Build a context from task.inputs for guard evaluation
        context = dict(task.inputs or {})

        for guard in guards:
            condition = guard.get("condition", "true")
            if not _eval_simple_condition(condition, context):
                continue

            # Matched guard
            if "action" in guard:
                action = guard["action"]
                if action.get("type") == "return":
                    # immediate return: produce no sub_tasks and set outputs via task.result
                    outputs = action.get("outputs", {})
                    # map simple strings like "[]" or "numbers" into actual values
                    resolved = {}
                    for k, v in outputs.items():
                        if isinstance(v, str) and v.strip() == "[]":
                            resolved[k] = []
                        elif isinstance(v, str) and v.strip() in context:
                            resolved[k] = context.get(v.strip())
                        else:
                            resolved[k] = v
                    task.result = resolved
                    return DecompositionResult(
                        sub_tasks=[],
                        decomposition_strategy="none",
                        recombination_plan="direct",
                        reasoning=f"Return action for guard {condition}"
                    )

            if "decomposition" in guard:
                decomp = guard["decomposition"]
                strategy = decomp.get("strategy", "hierarchical")
                if strategy == "choice":
                    # alternatives present
                    alts = decomp.get("alternatives", [])
                    alt_plans = []
                    for alt in alts:
                        plan = alt.get("plan", [])
                        tasks = self._plan_to_tasks(plan, parent_id=task.id, parent_inputs=task.inputs)
                        alt_plans.append(tasks)
                    return DecompositionResult(
                        sub_tasks=[],
                        decomposition_strategy="choice",
                        recombination_plan=decomp.get("recombination", "merge"),
                        reasoning="choice decomposition from YAML",
                        alternatives=alt_plans
                    )
                else:
                    # hierarchical: return sub_tasks from plan
                    plan = decomp.get("plan", [])
                    sub_tasks = self._plan_to_tasks(plan, parent_id=task.id, parent_inputs=task.inputs)
                    recomb = decomp.get("recombination", "merge") or "merge"
                    return DecompositionResult(
                        sub_tasks=sub_tasks,
                        decomposition_strategy="hierarchical",
                        recombination_plan=recomb,
                        reasoning="hierarchical decomposition from YAML"
                    )

        # No guard matched: fallback
        return DecompositionResult(
            sub_tasks=[],
            decomposition_strategy="none",
            recombination_plan="direct",
            reasoning="No guard matched"
        )

    def _plan_to_tasks(self, plan: List[Dict[str, Any]], parent_id: str, parent_inputs: Optional[Dict[str, Any]] = None) -> List[Task]:
        tasks: List[Task] = []
        for node in plan:
            try:
                print(f"[LOADER] plan node raw: {node}")
            except Exception:
                pass
            nid = node.get("id") or f"{parent_id}.node{len(tasks)+1}"
            ntype = node.get("type", "tool")
            params = node.get("params", {})
            description = params.get("behavior") or ntype
            inputs = {}
            # node may declare inputs mapping: try top-level 'inputs' or 'params.inputs'
            declared_inputs = node.get("inputs") or node.get("params", {}).get("inputs")
            if declared_inputs:
                for dst, src in declared_inputs.items():
                    if isinstance(src, str) and parent_inputs and src in parent_inputs:
                        inputs[dst] = parent_inputs.get(src)
                    else:
                        inputs[dst] = src
            else:
                # If no explicit inputs declared, inherit parent inputs by default
                if parent_inputs:
                    inputs = dict(parent_inputs)

            # workflow nodes represent nested calls; treat them as non-atomic
            is_atomic = ntype != "workflow"
            outputs = node.get('outputs') or node.get('params', {}).get('outputs') or {}
            task = Task(
                id=nid,
                description=description,
                inputs=inputs,
                params=params,
                is_atomic=is_atomic,
                verification_criteria=node.get("tests", []),
                parent_id=parent_id
            )
            # store declared outputs mapping (parent_key -> child_key)
            try:
                task.outputs = outputs
            except Exception:
                task.outputs = {}
            # debug visibility when running examples
            try:
                print(f"[LOADER] created task {nid} inputs={inputs}")
            except Exception:
                pass
            tasks.append(task)
        return tasks

    def _nodes_to_tasks(self, nodes: List[Dict[str, Any]], parent_id: str, root_inputs: Optional[Dict[str, Any]] = None) -> List[Task]:
        """Convert engine-style nodes into Task objects in topological order.

        This is a lightweight mapper: it preserves node ids, descriptions, and io
        declarations. Inputs are resolved from root_inputs when possible; otherwise
        left as None/placeholders. Execution order is topologically sorted using
        edges declared in the spec.
        """
        # Build id->node map
        id_map = {n.get('id'): n for n in nodes}

        # If edges exist in the spec, use them to topologically sort; else keep original order
        edges = self.spec.get('edges', [])
        if edges:
            # Build adjacency and indegree
            indegree = {nid: 0 for nid in id_map}
            adj = {nid: [] for nid in id_map}
            for e in edges:
                src = e.get('from') or e.get('src')
                dst = e.get('to') or e.get('dest')
                if src in id_map and dst in id_map:
                    adj[src].append(dst)
                    indegree[dst] = indegree.get(dst, 0) + 1

            # Kahn's algorithm
            queue = [nid for nid, deg in indegree.items() if deg == 0]
            ordered = []
            while queue:
                cur = queue.pop(0)
                ordered.append(id_map[cur])
                for nb in adj.get(cur, []):
                    indegree[nb] -= 1
                    if indegree[nb] == 0:
                        queue.append(nb)
        else:
            ordered = nodes

        tasks: List[Task] = []
        for node in ordered:
            nid = node.get('id')
            desc = node.get('description') or node.get('params', {}).get('behavior') or node.get('type')
            io = node.get('io', {}) or {}
            inputs = {}
            for inp in io.get('inputs', []):
                # Try to resolve from root inputs; otherwise leave None
                if root_inputs and inp in root_inputs:
                    inputs[inp] = root_inputs.get(inp)
                else:
                    inputs[inp] = None

            tests = node.get('tests', [])
            # Treat workflow and non-workflow types similarly; MetaAgent will decide
            is_atomic = True
            task = Task(
                id=nid,
                description=desc,
                inputs=inputs,
                is_atomic=is_atomic,
                verification_criteria=tests,
                parent_id=parent_id
            )
            # attach declared outputs and incoming guard conditions for runtime use
            task.io_outputs = io.get('outputs', [])
            incoming = [e for e in self.spec.get('edges', []) if (e.get('to') or e.get('dest')) == nid]
            task.guard_conditions = [e.get('when', 'true') for e in incoming]
            tasks.append(task)

        return tasks

    


def load_yaml_to_meta_agent(yaml_path: str):
    """Load a high-level YAML and return the root task and decomposer

    The returned `root_task` should be passed to `MetaAgent.solve(root_task)` with a
    MetaAgent constructed using the returned decomposer.
    """
    with open(yaml_path, "r") as fh:
        parsed = yaml.safe_load(fh)

    # Create a top-level Task representing the workflow invocation
    name = parsed.get("name", "workflow")
    root = Task(
        id=name,
        description=parsed.get("description", ""),
        inputs={},
        is_atomic=False,
        verification_criteria=parsed.get("tests", [])
    )

    decomposer = YamlTaskDecomposer(parsed)
    # Build verifier and combiner from YAML if provided
    verifier = _build_verifier_from_spec(parsed)
    combiner = _build_combiner_from_spec(parsed)

    return root, decomposer, verifier, combiner


def _build_combiner_from_spec(parsed: Dict[str, Any]):
    """Create a combiner instance based on YAML spec.

    Supported combiner types:
      - concatenate: concatenate list outputs from sub-results into a single list
      - default: use generic ResultCombiner
    """
    spec = parsed.get('combiner') or {}
    ctype = spec.get('type') if isinstance(spec, dict) else None

    if ctype == 'concatenate':
        left_key = spec.get('left_key')
        right_key = spec.get('right_key')
        out_key = spec.get('output_key', 'sorted_numbers')

        class ConcatenateCombiner:
            def __init__(self, left_key, right_key, out_key):
                self.left_key = left_key
                self.right_key = right_key
                self.out_key = out_key

            def _find_list_by_key(self, key, sub_results):
                for r in sub_results:
                    res = r.get('result') or {}
                    if isinstance(res, dict) and key in res and isinstance(res[key], list):
                        return res[key]
                return None

            def _find_two_lists(self, sub_results):
                lists = []
                for r in sub_results:
                    res = r.get('result') or {}
                    if isinstance(res, dict):
                        for k, v in res.items():
                            if isinstance(v, list):
                                lists.append((k, v))
                    elif isinstance(res, list):
                        lists.append((None, res))
                return lists

            def combine(self, task: Task, sub_tasks: List[Task], sub_results: List[Dict[str, Any]], recombination_plan: str):
                # If any sub-result already provides the final output (e.g. merge tool), prefer it.
                # Prefer the final sub-result that provides the desired out_key (e.g., merge tool -> final sorted list)
                for r in reversed(sub_results):
                    res = r.get('result') or {}
                    if isinstance(res, dict) and self.out_key in res and isinstance(res[self.out_key], list):
                        return {self.out_key: res[self.out_key]}

                left = None
                right = None
                if self.left_key and self.right_key:
                    left = self._find_list_by_key(self.left_key, sub_results)
                    right = self._find_list_by_key(self.right_key, sub_results)

                if left is None or right is None:
                    lists = self._find_two_lists(sub_results)
                    name_map = {k: v for k, v in lists}
                    # prefer named keys
                    for candidate in ('left_sorted', 'left'):
                        if candidate in name_map and left is None:
                            left = name_map[candidate]
                    for candidate in ('right_sorted', 'right'):
                        if candidate in name_map and right is None:
                            right = name_map[candidate]

                    if (left is None or right is None) and len(lists) >= 2:
                        if left is None:
                            left = lists[0][1]
                        if right is None:
                            right = lists[1][1]

                if (left is None or right is None):
                    for r in sub_results:
                        res = r.get('result') or {}
                        if isinstance(res, dict):
                            if left is None and 'left' in res and isinstance(res['left'], list):
                                left = res['left']
                            if right is None and 'right' in res and isinstance(res['right'], list):
                                right = res['right']

                combined_list = []
                if left and right:
                    combined_list = list(left) + list(right)
                else:
                    for _, v in self._find_two_lists(sub_results):
                        combined_list.extend(v)

                return {out_key: combined_list}

        return ConcatenateCombiner(left_key, right_key, out_key)

    # fallback
    return ResultCombiner()


def _build_verifier_from_spec(parsed: Dict[str, Any]):
    """Create a verifier instance based on YAML spec.

    Supported verifier types:
      - default: use generic TaskVerifier
    """
    # For now, return the default minimal TaskVerifier for the demo.
    return TaskVerifier()
