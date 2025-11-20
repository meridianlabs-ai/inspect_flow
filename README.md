# Inspect Flow

Workflow orchestration for [Inspect AI](https://inspect.aisi.org.uk/) that enables you to run evaluations at scale with repeatability and maintainability.

## Why Inspect Flow?

As evaluation workflows grow in complexity—running multiple tasks across different models with varying parameters—managing these experiments becomes challenging. Inspect Flow addresses this by providing:

- **Declarative Configuration**: Define your entire evaluation pipeline in type-safe Pydantic schemas
- **Repeatability**: Encapsulated Python dependencies for each workflow
- **Parameter Sweeping**: Matrix execution patterns for systematic exploration across tasks and models

Inspect Flow is designed for researchers and engineers running systematic AI evaluations who need to scale beyond ad-hoc scripts.

## Quick Start

### Installation

```bash
pip install git+https://github.com/meridianlabs-ai/inspect_flow
```

### Your First Evaluation

Create a `config.py` file:

```python
from inspect_flow import FlowJob, FlowTask

FlowJob(
    dependencies=["inspect-evals"],
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
        ),
        FlowTask(
            name="inspect_evals/mmlu_0_shot",
            model="openai/gpt-4o",
        ),
    ],
)
```

Run it:

```bash
flow run config.py
```

This creates a virtual environment, installs dependencies (including model-specific packages), and runs both evaluations.

### Parameter Sweeping

Want to test multiple models across multiple tasks? Use `tasks_matrix`:

```python
from inspect_flow import FlowJob, tasks_matrix

FlowJob(
    dependencies=["inspect-evals"],
    tasks=tasks_matrix(
        task=[
            "inspect_evals/gpqa_diamond",
            "inspect_evals/mmlu_0_shot",
        ],
        model=[
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
        ],
    ),
)
```

This runs 4 evaluations (2 tasks × 2 models). Preview the expanded config first:

```bash
flow config config.py
```

## Documentation

- **Usage**: End-to-end guide for developing and running Flow jobs
- **Reference**: Detailed API and CLI documentation

Visit the [documentation site](https://meridianlabs-ai.github.io/inspect_flow/) for more information.

## Development

To work on development of Inspect Flow, clone the repository and install with the `-e` flag and `[dev, doc]` optional dependencies:

```bash
git clone https://github.com/meridianlabs-ai/inspect_flow
cd inspect_flow
uv sync
source .venv/bin/activate
```

Optionally install pre-commit hooks via

```bash
make hooks
```

Run linting, formatting, and tests via

```bash
make check
make test
```
