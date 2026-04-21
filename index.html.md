# Inspect Flow

## Introduction

Inspect Flow is a workflow orchestration tool for [Inspect AI](https://inspect.aisi.org.uk/) that enables you to define, run, and manage evaluations at scale — from configuration through to production.

**Why Inspect Flow?** As evaluation workflows grow in complexity—running multiple tasks across different models with varying parameters, then reviewing, validating, and promoting results—managing these experiments becomes challenging. Inspect Flow addresses this by providing:

1.  [**Declarative Configuration**](./spec.html.md): Define complex evaluations with tasks, models, and parameters in type-safe schemas
2.  [**Global Log Reuse**](./store.html.md): Flow Store indexes evaluation logs and enables cross-directory reuse, so you only run what’s new or changed
3.  [**Powerful Defaults**](./defaults.html.md): Define defaults once and reuse them everywhere with automatic inheritance
4.  [**Parameter Sweeping**](./matrix.html.md): Matrix patterns for systematic exploration across tasks, models, and hyperparameters
5.  [**Post-Evaluation Workflows**](./steps.html.md): Tag, validate, and promote evaluation logs with composable steps

Inspect Flow is designed for researchers and engineers running systematic AI evaluations who need to scale beyond ad-hoc scripts.

## Getting Started

> **NOTE: NotePrerequisites**
>
> Before using Inspect Flow, you should:
>
> - Have familiarity with [Inspect AI](https://inspect.aisi.org.uk/)
> - Have an existing Inspect evaluation or use one from [inspect-evals](https://github.com/UKGovernmentBEIS/inspect_evals)

### Installation

Install the `inspect-flow` package from PyPI as follows:

``` bash
pip install inspect-flow
```

### Set up API keys

You’ll need API keys for the model providers you want to use. Set the relevant provider API key in your `.env` file or export it in your shell:

``` bash
export OPENAI_API_KEY=your-openai-api-key
```

``` bash
export ANTHROPIC_API_KEY=your-anthropic-api-key
```

``` bash
export GOOGLE_API_KEY=your-google-api-key
```

``` bash
export GROK_API_KEY=your-grok-api-key
```

``` bash
export MISTRAL_API_KEY=your-mistral-api-key
```

``` bash
export HF_TOKEN=your-hf-token
```

### Optional: VS Code extension

Optionally install the [Inspect AI VS Code Extension](https://inspect.aisi.org.uk/vscode.html) which includes features for viewing evaluation log files.

## Basic Example

Let’s walk through creating your first Flow configuration. We’ll use [FlowSpec](./reference/inspect_flow.html.md#flowspec) (the entrypoint class) and [FlowTask](./reference/inspect_flow.html.md#flowtask) to define evaluations.

> **TIP: TipCore Components Reference**
>
> - [FlowSpec](./reference/inspect_flow.html.md#flowspec) — Pydantic class that encapsulates the declarative description of a Flow spec.
> - [FlowTask](./reference/inspect_flow.html.md#flowtask) — Pydantic class abstraction on top of Inspect AI [Task](https://inspect.aisi.org.uk/tasks.html).
> - [FlowModel](./reference/inspect_flow.html.md#flowmodel) — Pydantic class abstraction on top of Inspect AI [Model](https://inspect.aisi.org.uk/models.html).
> - [tasks_matrix()](./reference/inspect_flow.html.md#tasks_matrix) — Helper function for parameter sweeping to generate a list of tasks with all parameter combinations.
> - [models_matrix()](./reference/inspect_flow.html.md#models_matrix) — Helper function for parameter sweeping to generate a list of models with all parameter combinations.
> - [configs_matrix()](./reference/inspect_flow.html.md#configs_matrix) — Helper function for parameter sweeping to generate a list of GenerateConfig with all parameter combinations.

[FlowSpec](./reference/inspect_flow.html.md#flowspec) is the main entrypoint for defining evaluation runs. At its core, it takes a list of tasks to run. Here’s a simple example that runs two evaluations:

    config.py

``` python
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

To run the evaluations, execute the following command. Make sure you have the necessary dependencies installed (like `inspect-evals` and `openai` for this example).

``` bash
flow run config.py
```

Both tasks will run with progress displayed in your terminal.

![](images/config_progress_terminal.png)

Progress bar in terminal

### Python API

You can run evaluations from Python instead of the command line by calling the [run()](./reference/inspect_flow.api.html.md#run) function with a [FlowSpec](./reference/inspect_flow.html.md#flowspec).

    config.py

``` python
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

Often you’ll want to evaluate multiple tasks across multiple models. Rather than manually defining every combination, use `tasks_matrix` to generate all task-model pairs:

    matrix.py

``` python
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

``` bash
flow config matrix.py
```

This command outputs the expanded configuration showing all 4 task-model combinations (2 tasks × 2 models).

    matrix.yml

``` yml
log_dir: logs
tasks:
- name: inspect_evals/gpqa_diamond
  model: openai/gpt-5
- name: inspect_evals/gpqa_diamond
  model: openai/gpt-5-mini
- name: inspect_evals/mmlu_0_shot
  model: openai/gpt-5
- name: inspect_evals/mmlu_0_shot
  model: openai/gpt-5-mini
```

Flow provides additional matrix functions (`models_matrix`, `configs_matrix`) for sweeping over model settings, generation configs, and more. See [Matrixing](./matrix.html.md) for details.

## Run Evaluations

Before running evaluations, preview what would run with `--dry-run`:

``` bash
flow run matrix.py --dry-run
```

This performs the full setup process—importing tasks from the registry, applying all defaults, expanding all matrix functions, and checking for existing logs—showing exactly what would run, but stops before actually running the evaluations.

To run the config:

``` bash
flow run matrix.py
```

When complete, you’ll find a link to the logs at the bottom of the task results summary.

![](images/logs_terminal.png)

Log path printed in terminal

To view logs interactively, run:

``` bash
inspect view --log-dir logs
```

![](images/inspect_view_eval.png)

Eval logs rendered by Inspect View

## After Running

Once evaluations complete, use [steps](./steps.html.md) to operate on the resulting logs. For example, tag logs after reviewing them:

``` bash
flow step tag logs/ --add reviewed --reason "Manually inspected"
```

Use `flow check` to verify the completeness of a spec against a log directory — for example, checking how much of a production directory has been filled:

``` bash
flow check matrix.py --log-dir s3://bucket/prod/logs
```

Steps can be composed into full workflows — filtering, tagging, and copying logs between directories. See [Steps](./steps.html.md) for custom steps, filters, and an end-to-end example.

## Learning More

See the following articles to learn more about using Flow:

- [Spec](./spec.html.md): Flow type system, config structure and basics.
- [Flow Store](./store.html.md): How Flow indexes evaluation logs and enables cross-directory reuse across runs.
- [Defaults](./defaults.html.md): Define defaults once and reuse them everywhere with automatic inheritance.
- [Matrixing](./matrix.html.md): Systematic parameter exploration with matrix and with functions.
- [Steps](./steps.html.md): Post-evaluation workflows — tag, validate, and promote logs with composable steps.
- [Reference](./reference/index.html.md): Detailed documentation on the Flow Python API and CLI commands.
