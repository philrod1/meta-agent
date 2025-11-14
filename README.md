# Meta-Agent Workflow System

A Python framework for LLM-assisted workflow specification and meta-agent orchestration.
Converts human-readable task descriptions into validated, executable DAG workflows.

## Architecture Overview

```
Human Spec (free text)
    ->  (LLM interpretation)
Intermediate Spec (structured)
    ->  (LLM YAML generation)
YAML Workflow (validated)
    ->  (Meta-agent compilation)
Executable DAG + Tests
```

## Components

### 1. Workflow Engine (src/workflow/)

Executes pre-defined DAG workflows from YAML specifications.

- `compiler.py` - Load and validate workflow YAML files
- `executor.py` - Execute workflow DAG with guards and verification
- `guards.py` - AST-based safe expression evaluation for conditions
- `models.py` - Data models (Workflow, Node, Edge)
- `context.py` - Execution context management
- `factory.py` - Workflow component factory

### 2. Meta-Agent System (src/meta_agent.py)

Orchestrates task decomposition, execution, verification, and recombination.

Core cycle:
1. Receive high-level task specification
2. Decompose into simpler, verifiable sub-tasks (recursive)
3. Execute each sub-task
4. Verify each sub-task result
5. Recombine all results into final solution

Components:
- `MetaAgent` - Top-level orchestrator
- `TaskDecomposer` - Breaks tasks into sub-tasks
- `TaskExecutor` - Executes atomic tasks
- `TaskVerifier` - Validates results against criteria
- `ResultCombiner` - Merges sub-task results

### 3. Agent System (src/agents/)

- `base.py` - Base agent interface
- `router.py` - Agent routing logic
- `tool.py` - Tool execution wrapper
- `approval.py` - Human-in-the-loop approval

### 4. Tool Registry (src/tools/)

- `registry.py` - Centralized tool registration and lookup

## Installation

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Running the Meta-Agent Demo

```bash
PYTHONPATH=. python examples/meta_agent_mvp_demo.py
```

Demonstrates:
- Simple task decomposition
- Sequential task chains
- Nested recursive decomposition
- Atomic task execution

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test suites
pytest tests/test_workflow_compiler.py -v
pytest tests/test_workflow_executor.py -v
pytest tests/test_meta_agent.py -v
pytest tests/test_guards.py -v
```


### Creating a Workflow

See `workflows/order_refund.yaml` for example structure:

```yaml
name: order_refund_workflow
description: Process customer refund request
preconditions:
  - order_id is not none
success_criteria:
  - refund_processed
nodes:
  - id: load_order
    type: tool
    params:
      tool: get_order
  - id: validate_payment
    type: tool
    params:
      tool: check_payment_status
edges:
  - src: load_order
    dest: validate_payment
    when: order_loaded
```

Load and execute:

```python
from src.workflow.compiler import load_workflow
from src.workflow.executor import run_workflow

workflow = load_workflow('workflows/order_refund.yaml')
result = run_workflow(workflow, initial_context={'order_id': 'ORD-123'})
```

## Project Structure

```
meta_agent/
  examples/           # Demo scripts and examples
  prompts/            # LLM prompts for spec generation
  schemas/            # JSON/YAML schemas for validation
  specs/              # Example workflow specifications
    human/            # Free-text task descriptions
    intermediate/     # Structured specifications
    yaml/             # Generated YAML workflows
  src/
    agents/           # Agent implementations
    tools/            # Tool registry and definitions
    workflow/         # Workflow engine core
    meta_agent.py     # Meta-agent orchestration
    llm_api.py        # LLM interface
  tests/              # Test suite
  workflows/          # Compiled workflow files
```

## Development Status

### Completed
- Workflow DAG execution engine
- Guard evaluation with safe AST parsing
- Agent and tool infrastructure
- Meta-agent MVP with recursive decomposition
- Comprehensive test suite (61 tests passing)

### Unimplemented Ideas
- LLM integration for task decomposition
- Workflow engine integration with meta-agent
- Pattern library for decomposition reuse
- Parallel sub-task execution
- Advanced verification strategies
- Workflow YAML generation from decomposition
- Interactive debugging tools

## Requirements

- Python 3.12+
- pytest 9.0.0+
- PyYAML
