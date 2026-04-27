<img src="https://raw.githubusercontent.com/meridianlabs-ai/inspect_flow/main/docs/images/icon-dark.svg" alt="Inspect Flow" width="50" height="50">

# Inspect Flow

Workflow orchestration for [Inspect AI](https://inspect.aisi.org.uk/) that enables you to define, run, and manage evaluations at scale — from configuration through to production.

## Why Inspect Flow?

As evaluation workflows grow in complexity—running multiple tasks across different models with varying parameters, then reviewing, validating, and promoting results—managing these experiments becomes challenging. Inspect Flow addresses this by providing:

1. **Declarative Configuration**: Define complex evaluations with tasks, models, and parameters in type-safe schemas
2. **Repeatable & Shareable**: Encapsulated definitions of tasks, models, configurations, and Python dependencies ensure experiments can be reliably repeated and shared
3. **Powerful Defaults**: Define defaults once and reuse them everywhere with automatic inheritance
4. **Parameter Sweeping**: Matrix patterns for systematic exploration across tasks, models, and hyperparameters
5. **Post-Evaluation Workflows**: Tag, validate, and promote evaluation logs with composable steps

Inspect Flow is designed for researchers and engineers running systematic AI evaluations who need to scale beyond ad-hoc scripts.

## Getting Started

### Prerequisites

Before using Inspect Flow, you should:

- Have familiarity with [Inspect AI](https://inspect.aisi.org.uk/)
- Have an existing Inspect evaluation or use one from [inspect-evals](https://github.com/UKGovernmentBEIS/inspect_evals)

### Installation

```bash
pip install inspect-flow
```

### Optional: VS Code extension

Optionally install the [Inspect AI VS Code Extension](https://inspect.aisi.org.uk/vscode.html) which includes features for viewing evaluation log files.

## Basic Example

`FlowSpec` is the main entrypoint for defining evaluation runs. At its core, it takes a list of tasks to run. Here's a simple example that runs two evaluations:

```python
from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",
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

To run the evaluations, run the following command in your shell. This will create a virtual environment for this spec run and install the dependencies. Note that task and model dependencies (like the `inspect-evals` and `openai` Python packages) are inferred and installed automatically.

```bash
flow run config.py
```

This will run both tasks and display progress in your terminal.

![Progress bar in terminal](https://raw.githubusercontent.com/meridianlabs-ai/inspect_flow/main/docs/images/config_progress_terminal.png)

### Python API

You can run evaluations from Python instead of the command line.

```python
from inspect_flow import FlowSpec, FlowTask
from inspect_flow.api import run

spec = FlowSpec(
    log_dir="logs",
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
run(spec=spec)
```

## Matrix Functions

Often you'll want to evaluate multiple tasks across multiple models. Rather than manually defining every combination, use `tasks_matrix` to generate all task-model pairs:

```python
from inspect_flow import FlowSpec, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
            "inspect_evals/gpqa_diamond",
            "inspect_evals/mmlu_0_shot",
        ],
        model=[
            "openai/gpt-5",
            "openai/gpt-5-mini",
        ],
    ),
)
```

To preview the expanded config before running it, you can run the following command in your shell to ensure the generated config is the one that you intend to run.

```bash
flow config matrix.py
```

This command outputs the expanded configuration showing all 4 task-model combinations (2 tasks × 2 models).

```yaml
log_dir: logs
dependencies:
- inspect-evals
tasks:
- name: inspect_evals/gpqa_diamond
  model:
    name: openai/gpt-5
- name: inspect_evals/gpqa_diamond
  model:
    name: openai/gpt-5-mini
- name: inspect_evals/mmlu_0_shot
  model:
    name: openai/gpt-5
- name: inspect_evals/mmlu_0_shot
  model:
    name: openai/gpt-5-mini
```

Flow provides additional matrix functions (`models_matrix`, `configs_matrix`) for sweeping over model settings, generation configs, and more. See [Matrixing](https://meridianlabs-ai.github.io/inspect_flow/matrix.html) for details.

## Run Evaluations

Before running evaluations, preview what would run with `--dry-run`:

```bash
flow run matrix.py --dry-run
```

This performs the full setup process—importing tasks from the registry, applying all defaults, expanding all matrix functions, and checking for existing logs—showing exactly what would run, but stops before actually running the evaluations.

To run the config:

```bash
flow run matrix.py
```

When complete, you'll find a link to the logs at the bottom of the task results summary.

![Log path printed in terminal](https://raw.githubusercontent.com/meridianlabs-ai/inspect_flow/main/docs/images/logs_terminal.png)

To view logs interactively, run:

```bash
inspect view --log-dir logs
```

![Eval logs rendered by Inspect View](https://raw.githubusercontent.com/meridianlabs-ai/inspect_flow/main/docs/images/inspect_view_eval.png)

## After Running

Once evaluations complete, use [steps](https://meridianlabs-ai.github.io/inspect_flow/steps.html) to operate on the resulting logs. For example, tag logs after reviewing them:

```bash
flow step tag logs/ --add reviewed --reason "Manually inspected"
```

Use `flow check` to verify the completeness of a spec against a log directory — for example, checking how much of a production directory has been filled:

```bash
flow check matrix.py --log-dir s3://bucket/prod/logs
```

Steps can be composed into full workflows — filtering, tagging, and copying logs between directories. See [Steps](https://meridianlabs-ai.github.io/inspect_flow/steps.html) for custom steps, filters, and an end-to-end example.

## Learning More

See the following articles to learn more about using Flow:

- [Spec](https://meridianlabs-ai.github.io/inspect_flow/spec.html): Flow type system, config structure and basics.
- [Defaults](https://meridianlabs-ai.github.io/inspect_flow/defaults.html): Define defaults once and reuse them everywhere with automatic inheritance.
- [Matrixing](https://meridianlabs-ai.github.io/inspect_flow/matrix.html): Systematic parameter exploration with matrix and with functions.
- [Steps](https://meridianlabs-ai.github.io/inspect_flow/steps.html): Post-evaluation workflows — tag, validate, and promote logs with composable steps.
- [Reference](https://meridianlabs-ai.github.io/inspect_flow/reference/): Detailed documentation on the Flow Python API and CLI commands.

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
