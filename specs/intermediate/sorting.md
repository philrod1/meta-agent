# Sorting Task — Intermediate Spec

This document converts the free-text human spec into a semi-structured intermediate specification suitable for LLM-to-YAML generation.

## Title

Sorting (divide-and-conquer) using Agent Workflow

## Purpose

Sort a list of integers using a divide-and-conquer strategy implemented as an agent workflow. The workflow should decompose a top-level Sort task into smaller subtasks (base cases and recursive splits), execute them, and recombine the sorted sub-results into a final sorted list.

## Inputs

- `numbers`: List[int] — the list of integers to sort

## Outputs

- `sorted_numbers`: List[int] — the sorted list of integers (ascending order by default)
- `steps`: Optional[List[str]] — an execution trace or list of steps taken (useful for testing)

## Preconditions

- `numbers` is provided (not null). If empty list, return empty list.

## Success / Verification Criteria

- `sorted_numbers` is ordered ascendingly (every element <= next element)
- `sorted_numbers` is a permutation of input `numbers` (same multiset/counts)

## Decomposition Strategy

Decomposition type: `hierarchical` (divide-and-conquer)

- Base cases (atomic tasks):
  - If list length == 0: return [] (atomic)
  - If list length == 1: return the list as-is (atomic)
  - If list length == 2: compare two elements and return ordered pair (atomic)
    - Choice option: when length == 2 the decomposer may offer a `choice` between:
      1. Treating it as a base case (compare and return ordered pair)
      2. Splitting into two singleton lists and then merging (split -> Sort(left)=[a], Sort(right)=[b] -> Merge)
    This demonstrates the `choice` decomposition strategy (alternatives where only one needs to succeed).

- Recursive case:
  - Split `numbers` into two sublists (left, right), preferably balanced
  - Create two sub-tasks: Sort(left), Sort(right)
  - After sub-tasks complete, merge the two sorted sub-results into a single sorted list

Recombination plan: `merge` — standard merge of two sorted lists that preserves multiplicities

## Task Definitions (semi-structured)

- Task: `Sort` (parent)
  - Description: "Sort a list of integers using divide-and-conquer"
  - Inputs: `numbers`
  - Verification: see Success / Verification Criteria
  - Decomposes to: either atomic base-case tasks or two `Sort` subtasks followed by `Merge`

- Atomic Task: `SortBase` (handles lengths 0,1,2)
  - Description: "Return sorted list for small lengths"
  - Inputs: `numbers`
  - Outputs: `sorted_numbers`
  - Behavior: if len=0 -> []; if len=1 -> [x]; if len=2 -> [min,max]

- Task: `Split` (optional explicit step)
  - Description: "Split list into left/right sublists"
  - Inputs: `numbers`
  - Outputs: `left`, `right`

- Task: `Merge`
  - Description: "Merge two sorted lists into one"
  - Inputs: `left_sorted`, `right_sorted`
  - Outputs: `sorted_numbers`

## Execution Notes / Constraints

- Prefer balanced splits to minimize recursion depth.
- If lists are extremely large, the decomposer or executor may need to enforce a maximum recursion depth or switch to an in-place iterative merge to control memory usage.
- Ensure that `Merge` is stable and efficient.

## Edge Cases

- Duplicate values in input
- Empty list
- Very large lists (resource constraints)
- Non-integer values in `numbers` (validation should enforce integer type)

## LLM Hints for YAML Generation

Provide these when prompting the LLM to generate workflow YAML:

- Explicitly enumerate the base cases and their guard conditions:
  - `len(numbers) == 0`
  - `len(numbers) == 1`
  - `len(numbers) == 2`

- If you want to model a `choice` decomposition for `len(numbers) == 2`, express alternatives for that guard. For example:

  ```yaml
  - guard: "len(numbers) == 2"
    decomposition_strategy: "choice"
    alternatives:
      - plan: # alternative 1 - base case
        - id: sort_base
          type: tool
          params:
            behavior: "compare_and_return"
      - plan: # alternative 2 - split then merge
        - id: split
          type: tool
          params:
            behavior: "split_into_singletons"
        - id: sort_left
          type: workflow
          params:
            call: Sort
        - id: sort_right
          type: workflow
          params:
            call: Sort
        - id: merge
          type: tool
          params:
            behavior: "join_two_sorted_lists"
  ```

  This makes the LLM produce an explicit alternative list under the `len(numbers) == 2` guard. Prefer the simple sequential-fallback semantics by default (try plan 1, then plan 2).

- For the recursive branch, show the split and indicate that `Sort` is called on each sublist.
- Represent `Merge` as a node that depends on completion of both `Sort(left)` and `Sort(right)`.
- Add verification tests (simple unit-test-like assertions) to nodes where possible (e.g., ensure `SortBase` returns ordered pair).

## Example (informal)

- Input: `[3,1,4,1,5,9,2]`
- Decompose: split into `[3,1,4]` and `[1,5,9,2]` (example)
- Recurse: sort each, then Merge
- Output: `[1,1,2,3,4,5,9]`

## Next step

Use this intermediate markdown as the source to prompt the LLM for YAML workflow generation (conforming to `schemas/workflow-schema.json`).
