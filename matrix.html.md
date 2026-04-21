# Matrixing – Inspect Flow

Matrixing lets you systematically explore evaluation configurations by generating Cartesian products of parameters. Instead of manually writing every combination, Flow provides `*_matrix()` and `*_with()` functions to declaratively generate evaluation grids.

> **NOTE: Note**
>
> `*_matrix()` and `*_with()` functions work with Flow types ([FlowTask](./reference/inspect_flow.html.md#flowtask), [FlowModel](./reference/inspect_flow.html.md#flowmodel), [FlowSolver](./reference/inspect_flow.html.md#flowsolver), [FlowAgent](./reference/inspect_flow.html.md#flowagent)) and strings (for registry references). They cannot operate directly on Inspect AI objects (`Task`, `Model`, `Solver`, `Agent`).

## Matrix Functions

Matrix functions generate all combinations of their parameters using Cartesian products.

### tasks_matrix()

Generate task configurations by combining tasks with models, configs, solvers, and arguments:

    tasks_matrix.py

``` python
from inspect_flow import FlowSpec, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=["inspect_evals/gpqa_diamond", "inspect_evals/mmlu_0_shot"],
        model=["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
    ),
)
```

This creates **4 tasks** (2 tasks × 2 models).

In addition to `model`, `config`, `solver`, and `args`, you can also sweep over sample limit fields: `message_limit`, `token_limit`, `time_limit`, `working_limit`, and `cost_limit`. See [this example](https://github.com/meridianlabs-ai/inspect_flow/blob/main/examples/tasks_matrix_limits.py) for usage.

### models_matrix()

Generate model configurations with different generation settings:

    models_matrix.py

``` python
from inspect_ai.model import GenerateConfig
from inspect_flow import FlowSpec, models_matrix, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
            "inspect_evals/gpqa_diamond",
            "inspect_evals/mmlu_0_shot",
        ],
        model=models_matrix(
            model=[
                "openai/gpt-5",
                "openai/gpt-5-mini",
            ],
            config=[
                GenerateConfig(reasoning_effort="minimal"),
                GenerateConfig(reasoning_effort="low"),
                GenerateConfig(reasoning_effort="medium"),
                GenerateConfig(reasoning_effort="high"),
            ],
        ),
    ),
)
```

This creates **16 tasks** (2 task × 2 models × 4 resoning_effort).

### configs_matrix()

Generate generation config combinations by specifying individual parameters:

    configs_matrix.py

``` python
from inspect_flow import FlowSpec, configs_matrix, models_matrix, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
            "inspect_evals/gpqa_diamond",
            "inspect_evals/mmlu_0_shot",
        ],
        model=models_matrix(
            model=[
                "openai/gpt-5",
                "openai/gpt-5-mini",
            ],
            config=configs_matrix(
                reasoning_effort=["minimal", "low", "medium", "high"],
            ),
        ),
    ),
)
```

This creates **16 tasks** (2 task × 2 models × 4 resoning_effort).

### solvers_matrix()

Generate solver configurations with different arguments:

    solvers_matrix.py

``` python
from inspect_flow import FlowSpec, solvers_matrix, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=solvers_matrix(
            solver="chain_of_thought",
            args=[
                {"max_iterations": 3},
                {"max_iterations": 5},
                {"max_iterations": 10},
            ],
        ),
    ),
)
```

This creates **3 tasks** (1 task × 3 solver configurations).

### agents_matrix()

Generate agent configurations with different arguments:

    agents_matrix.py

``` python
from inspect_ai.tool import bash, python, web_search
from inspect_flow import FlowSpec, agents_matrix, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=agents_matrix(
            agent="react",
            args=[
                {"tools": [web_search()]},
                {"tools": [bash(), python()]},
                {"tools": [web_search(), bash(), python()]},
            ],
        ),
    ),
)
```

This creates **3 tasks** (1 task × 3 agent configurations).

## With Functions (Apply to All)

“With” functions apply the same setting to all items in a list, without creating a Cartesian product. Unlike matrix functions which multiply combinations, with functions keep the list size the same.

**Key difference:**

- **Matrix functions** create all combinations: `models_matrix(model=[A, B], temperature=[0.5, 1.0])` → 4 tasks (A at 0.5, A at 1.0, B at 0.5, B at 1.0)
- **With functions** apply to each item: `models_with(model=[A, B], temperature=0.5)` → 2 tasks (A at 0.5, B at 0.5)

### tasks_with()

Apply common settings to multiple tasks:

    tasks_with.py

``` python
from inspect_ai.model import GenerateConfig
from inspect_flow import FlowSpec, tasks_with

FlowSpec(
    tasks=tasks_with(
        task=["inspect_evals/gpqa_diamond", "inspect_evals/mmlu_0_shot"],
1        model="openai/gpt-4o",
2        config=GenerateConfig(temperature=0.7),
    )
)
```

1  
Apply the same model to both tasks

2  
Apply the same generation config to both tasks

This creates **2 tasks** (2 tasks, each with the same model and config).

### models_with()

Apply common settings to multiple models:

    models_with.py

``` python
from inspect_ai.model import GenerateConfig
from inspect_flow import FlowSpec, models_with, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        model=models_with(
            model=["openai/gpt-4o", "anthropic/claude-3-5-sonnet-20241022"],
1            config=GenerateConfig(temperature=0.7),
        ),
    ),
)
```

1  
Apply the same generation config to both models

This creates **2 tasks** (1 task × 2 models, each with the same config).

### configs_with()

Apply common settings to multiple configs:

    configs_with.py

``` python
from inspect_ai.model import GenerateConfig
from inspect_flow import FlowSpec, configs_with, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        config=configs_with(
            config=[
                GenerateConfig(temperature=0.0),
                GenerateConfig(temperature=0.5),
                GenerateConfig(temperature=1.0),
            ],
1            max_tokens=1000,
        ),
    ),
)
```

1  
Apply the same max_tokens to all three temperature configs

This creates **3 tasks** (1 task × 3 configs, each with the same max_tokens).

### solvers_with()

Apply common settings to multiple solvers:

    solvers_with.py

``` python
from inspect_flow import FlowSpec, solvers_with, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=solvers_with(
            solver=["chain_of_thought", "plan_solve", "self_critique"],
            args={"max_steps": 5},
        ),
    ),
)
```

This creates **3 tasks** (1 task × 3 solvers, each with the same max_attempts).

### agents_with()

Apply common settings to multiple agents:

    agents_with.py

``` python
from inspect_flow import FlowSpec, agents_with, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="my_task",
        solver=agents_with(
            agent=["system_message", "tool_agent", "web_agent"],
            args={"system_message": "You are a helpful assistant."},
        ),
    ),
)
```

This creates **3 tasks** (1 task × 3 agents, each with cache enabled).

### Combining Matrix and With

Mix parameter sweeps with common settings:

    matrix_and_with.py

``` python
from inspect_flow import (
    FlowSpec,
    configs_matrix,
    tasks_matrix,
    tasks_with,
)

FlowSpec(
    log_dir="logs",
    tasks=tasks_with(
1        task=tasks_matrix(
            task=["task1", "task2"],
            config=configs_matrix(
                temperature=[0.0, 0.5, 1.0],
            ),
        ),
2        model="openai/gpt-4o",
3        sandbox="docker",
    ),
)
```

1  
Create a matrix of 6 tasks (2 tasks × 3 temperature values)

2  
Apply the same model to all 6 tasks from the matrix

3  
Apply the same sandbox to all 6 tasks from the matrix

## Nested Sweeps

Matrix functions can be nested to create complex parameter grids. Use the unpacking operator `*` to expand inner matrix results:

**Example: Tasks with nested model sweep**

    nested_model_sweep.py

``` python
from inspect_ai.model import GenerateConfig
from inspect_flow import FlowSpec, models_matrix, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=["inspect_evals/mmlu_0_shot", "inspect_evals/gpqa_diamond"],
1        model=[
2            "anthropic/claude-3-5-sonnet",
3            *models_matrix(
                model=["openai/gpt-4o", "openai/gpt-4o-mini"],
                config=[
                    GenerateConfig(reasoning_effort="low"),
                    GenerateConfig(reasoning_effort="high"),
                ],
            ),
        ],
    ),
)
```

1  
Total of 5 models: 1 single model + 4 from the matrix (2 models × 2 reasoning_effort values)

2  
A single model configuration for Claude

3  
Use the unpacking operator `*` to expand the nested model matrix into the list

This creates **10 tasks** (2 tasks × 5 model configurations).

**Example: Tasks with nested task sweep**

    nested_task_sweep.py

``` python
from inspect_flow import FlowSpec, FlowTask, tasks_matrix

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task=[
1            FlowTask(name="task1", args={"subset": "test"}),
2            *tasks_matrix(
3                task="task2",
                args=[
                    {"language": "en"},
                    {"language": "de"},
                    {"language": "fr"},
                ],
            ),
        ],
        model=["model1", "model2"],
    ),
)
```

1  
A single task configuration with specific arguments

2  
Use the unpacking operator `*` to expand the nested task matrix into the list

3  
Total of 4 tasks: 1 single task + 3 from the matrix (1 task × 3 language variants)

This creates **8 tasks** (4 task variants × 2 models).

> **WARNING: WarningWatch Out for Combinatorial Explosion**
>
> Parameter sweeps grow multiplicatively. A sweep with:
>
> - 3 tasks
> - 4 models
> - 5 temperature values
> - 3 solver configurations
>
> Results in 3 × 4 × 5 × 3 = **180 evaluations**.
>
> Always preview with `--dry-run` to check the number of evaluations before running expensive grids.
>
> The [Flow Store](./store.html.md) indexes logs from every run. With `--store-read` enabled, re-running a large sweep only evaluates what’s new or changed.

## Matrix Merge

When base objects already have values, matrix parameters are merged:

``` python
tasks_matrix(
    task=FlowTask(
        name="task",
1        config=GenerateConfig(temperature=0.5)
    ),
    config=[
2        GenerateConfig(max_tokens=1000),
        GenerateConfig(max_tokens=2000),
    ]
)
```

1  
Base value of temperature=0.5

2  
Adds max_tokens, keeps temperature=0.5

This creates 2 tasks: one with `temperature=0.5, max_tokens=1000` and another with `temperature=0.5, max_tokens=2000`.
