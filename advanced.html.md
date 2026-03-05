# Advanced


## Execution Modes

Flow supports two execution modes that determine how your evaluations
run: **in-process (inproc)** and **virtual environment (venv)**.
Understanding these modes helps you choose the right approach for your
workflow.

### In-Process Mode (Default)

By default, Flow runs evaluations in your current Python process without
creating an isolated environment.

**Characteristics:**

- Runs directly in your current Python environment
- No automatic dependency installation—you manage packages yourself
- Supports direct use of Inspect AI objects (`Task`, `Model`, `Solver`,
  `Agent`)
- Faster startup (no environment creation overhead)
- Best for development, iteration, and when you control the environment

**Example:**

**inproc_mode.py**

``` python
from inspect_ai import Task
from inspect_ai.dataset import example_dataset
from inspect_ai.solver import generate
from inspect_flow import FlowSpec

FlowSpec(
    log_dir="logs",
    tasks=[
        Task(
            dataset=example_dataset("security_guide"),
            solver=generate(),
        ),
        "inspect_evals/gpqa_diamond",
    ],
)
```

Line 9  
Direct Inspect AI Task object (supported in inproc mode)

Line 13  
Registry reference works in both modes

### Virtual Environment Mode

Opt into virtual environment mode for isolated, reproducible evaluation
runs.

**Characteristics:**

- Creates a temporary virtual environment with
  [`uv`](https://github.com/astral-sh/uv) for each run
- Automatically installs dependencies from `pyproject.toml`, `uv.lock`,
  or `requirements.txt`
- Auto-detects and installs packages based on config (e.g.,
  `model="openai/gpt-4"` → installs `openai`)
- Cleans up the temporary environment after completion (logs persist in
  `log_dir`)
- Requires Flow types only—cannot use direct Inspect AI objects (`Task`,
  `Model`, etc.)
- Best for reproducibility and sharing

**Example:**

**venv_mode.py**

``` python
from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",
    execution_type="venv",
    python_version="3.11",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4",
        ),
    ],
)
```

Line 5  
Enable virtual environment mode

Line 6  
Optional: specify Python version

Or use the CLI flag:

``` bash
flow run config.py --venv
```

### Choosing Between Modes

| Consideration | In-Process (inproc) | Virtual Environment (venv) |
|----|----|----|
| **Default** | Yes ✓ | No (opt-in) |
| **Dependency installation** | Manual | Automatic |
| **Startup speed** | Fast | Slower (creates venv) |
| **Inspect AI objects** | Supported | Not supported |
| **Reproducibility** | Requires manual setup | Built-in |
| **Isolation** | Uses current environment | Fresh environment |
| **Best for** | Development, iteration | Production, sharing, CI/CD |

## Dependencies

This section details Flow’s dependency management system, which
primarily applies to virtual environment mode.

### Automatic Dependency Discovery

In virtual environment mode, Flow automatically discovers and installs
dependencies without requiring explicit configuration:

- **Dependency files**: Searches upward from your config file directory
  for `pyproject.toml` or `requirements.txt`. Relative paths will be
  resolved relative to the config file (when using the CLI) or
  `base_dir` arg (when using the API)
- **Package inference**: Detects packages from Flow type names in your
  config:
  - Models: `model="openai/gpt-4"` → installs `openai`
  - Tasks: `FlowTask(name="inspect_evals/mmlu")` → installs
    `inspect-evals`
  - Note: Package inference only works with Flow types (`FlowTask`,
    `FlowModel`, etc.), not direct Inspect AI objects

This means most workflows require no dependency configuration at all!

> [!NOTE]
>
> ### In-Process Mode Dependencies
>
> In in-process mode (the default), these files are **ignored** for
> automatic installation. You’re responsible for installing dependencies
> yourself using your preferred package manager (`uv`, `pip`, `conda`,
> etc.). However, you can still use the same `pyproject.toml` or
> `requirements.txt` files to manage your dependencies manually.
>
> Flow still generates a `flow-requirements.txt` file in your log
> directory to document what packages were installed when you ran the
> evaluation, helping with reproducibility.

> [!NOTE]
>
> ### Config Inheritance
>
> Flow automatically includes any `_flow.py` files in the config
> directory or parent directories (see
> [Inheritance](defaults.qmd#inheritance)). When these files specify
> `dependencies` in venv mode, those dependencies are automatically
> installed. This works in both execution modes—the inheritance
> mechanism applies everywhere, but dependency installation only happens
> in venv mode.

### Explicit Dependencies

While automatic dependency discovery works for most cases, you may need
explicit dependencies when you require specific package versions for
reproducibility e.g. `openai==2.8.0`, need to specify a non-standard
dependency file location, or need to override the automatic detection
behavior. Explicit dependencies give you full control over what gets
installed in your workflow’s virtual environment.

The `dependencies` field in `FlowSpec` accepts a `FlowDependencies`
object:

**config.py**

``` python
from inspect_flow import FlowDependencies, FlowSpec, FlowTask

FlowSpec(
    execution_type="venv",
    dependencies=FlowDependencies(
        dependency_file="../foo/pyproject.toml",
        additional_dependencies=["pandas==2.0.0"],
        auto_detect_dependencies=True,
    ),
    log_dir="logs",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-5",
        ),
    ],
)
```

Line 6  
How to find dependency files: Defaults to `"auto"` which auto-detects a
`requirements.txt` or a `pyproject.toml` file. May also be set to a path
to a dependency file or `"no_file"` to not use a dependency file. When
using `pyproject.toml`, if a `uv.lock` file exists in the same
directory, it will be used automatically for reproducible installs.

Line 7  
Extra packages beyond the dependency file. Accepts a string or list of
strings. Supports: PyPI packages, Git repositories, local packages.

Line 8  
Auto-install packages based on task and model names in the config
(default: `True`). For example, `model="openai/gpt-4"` installs
`openai`, and `name="inspect_evals/mmlu"` installs `inspect-evals`.

### Python Version

Specify the Python version for your spec’s virtual environment when
using venv mode:

**config.py**

``` python
from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    execution_type="venv",
    python_version="3.11",
    log_dir="logs",
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-5",
        ),
    ],
)
```

Line 4  
Required for python_version to take effect.

> [!NOTE]
>
> The `python_version` field only applies to virtual environment mode.
> In in-process mode, evaluations run using your current Python
> interpreter.

### Checking Config

To verify which dependencies and Python version will be used:

``` bash
flow run config.py --dry-run --venv
```

> [!TIP]
>
> ### Repeatability Best Practices
>
> For repeatable workflows, use **virtual environment mode** with the
> following practices:
>
> - **Enable venv mode**: Set `execution_type="venv"` in your `FlowSpec`
>   or use the `--venv` flag. This ensures isolated environments and
>   automatic dependency installation.
> - **Pin package versions**: Use exact versions for PyPI packages
>   (`"inspect-evals==0.3.15"`) and commit hashes for Git repositories
>   (`"git+https://github.com/user/repo@commit_hash"`).
> - **Specify Python version**: Explicitly set `python_version` (e.g.,
>   `"3.11"`) to ensure consistent Python environments.
> - **Use lockfiles**: When using `pyproject.toml`, include a `uv.lock`
>   file for fully reproducible dependency resolution (automatically
>   detected if present).
>
> This combination ensures your evaluations can be reliably repeated and
> shared with others.

## Parameterized Jobs

### Flow Args (`--arg`)

Pass custom variables to Python config files using `--arg` or the
`INSPECT_FLOW_ARG` environment variable. Use this for dynamic
configuration that isn’t available via `--set`. To access the args the
last statement in the config file should be a function that returns a
`FlowSpec`. This function will be called with any provided args:

``` bash
flow run config.py --arg task_min_priority=2
```

**config.py**

``` python
from inspect_flow import FlowSpec, FlowTask

all_tasks = [
    FlowTask(name="task_easy", flow_metadata={"priority": 1}),
    FlowTask(name="task_medium", flow_metadata={"priority": 2}),
    FlowTask(name="task_hard", flow_metadata={"priority": 3}),
]


def spec(task_min_priority: int = 1) -> FlowSpec:
    return FlowSpec(
        log_dir="logs",
        tasks=[
            t
            for t in all_tasks
            if (t.flow_metadata or {}).get("priority", 0) >= task_min_priority
        ],
    )
```

### Template Substitution

Use `{field_name}` syntax to reference other `FlowSpec` configuration
values. Substitutions are applied after the config is loaded:

``` python
FlowSpec(
    log_dir="logs/my_eval",
    options=FlowOptions(bundle_dir="{log_dir}/bundle"),
    # Result: bundle_dir="logs/my_eval/bundle"
)
```

For nested fields, use bracket notation: `{options[eval_set_id]}` or
`{flow_metadata[key]}`. Substitutions are resolved recursively until no
more remain.

#### Built-in Substitutions

In addition to `FlowSpec` field names, the following built-in
substitution keys are available:

| Key          | Description       | Example Output        |
|--------------|-------------------|-----------------------|
| `{DATETIME}` | Current timestamp | `2026-03-04T16-56-25` |

Built-in keys use uppercase names to distinguish them from `FlowSpec`
field names (which are lowercase). For example, `{DATETIME}` is a
built-in key while `{log_dir}` references the `log_dir` field.

## Metadata

Flow supports two types of metadata with distinct purposes: `metadata`
and `flow_metadata`.

### `metadata` (Inspect AI Metadata)

The `metadata` field in `FlowOptions` and `FlowTask` is passed directly
to Inspect AI and stored in evaluation logs. Use this for tracking
experiment information that should be accessible in Inspect AI’s log
viewer and analysis tools.

**Example:**

**config.py**

``` python
from inspect_flow import FlowOptions, FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",
    options=FlowOptions(
        metadata={
            "experiment": "baseline_v1",
            "hypothesis": "Higher temperature improves creative tasks",
            "hardware": "A100-80GB",
        }
    ),
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
            metadata={
                "task_variant": "chemistry_subset",
                "note": "Testing with reduced context",
            },
        )
    ],
)
```

The metadata from `FlowOptions` is applied globally to all tasks in the
evaluation run, while task-level metadata is specific to each task.
These metadata dictionaries are merged in Inspect AI, with task-level
metadata keys overriding the global options.

### `flow_metadata` (Flow-Only Metadata)

The `flow_metadata` field is available on `FlowSpec`, `FlowTask`,
`FlowModel`, `FlowScorer`, `FlowSolver`, and `FlowAgent`. This metadata
is **not passed to Inspect AI**—it exists only in the Flow configuration
and is useful for configuration-time logic and organization.

**Use cases:**

- Filtering or selecting configurations based on properties
- Organizing complex configuration generation logic
- Documenting configuration decisions
- Annotating configs without polluting Inspect AI logs

**Example: Configuration-time filtering**

**config.py**

``` python
from inspect_flow import FlowModel, FlowSpec, tasks_matrix

# Define models with metadata about capabilities
models = [
    FlowModel(name="openai/gpt-4o", flow_metadata={"context_window": 128000}),
    FlowModel(name="openai/gpt-4o-mini", flow_metadata={"context_window": 128000}),
    FlowModel(
        name="anthropic/claude-3-5-sonnet", flow_metadata={"context_window": 200000}
    ),
]

# Filter to only long-context models
long_context_models = [
    m for m in models if (m.flow_metadata or {}).get("context_window", 0) >= 128000
]

FlowSpec(
    log_dir="logs",
    tasks=tasks_matrix(
        task="long_context_task",
        model=long_context_models,
    ),
)
```

## Viewer Bundling

Viewer bundling works the same way as
[`eval_set()`](https://inspect.aisi.org.uk/eval-sets.html) in Inspect AI
and is configurable via `FlowOptions`. An additional feature allows you
to print bundle URLs for users running evaluations.

Convert local bundle paths to public URLs for sharing evaluation
results. The `bundle_url_mappings` in `FlowOptions` applies string
replacements to `bundle_dir` to generate a shareable URL that’s printed
to stdout after the evaluation completes.

**config.py**

``` python
from inspect_flow import FlowOptions, FlowSpec, FlowTask

FlowSpec(
    log_dir="logs/my_eval",
    options=FlowOptions(
        bundle_dir="s3://my-bucket/bundles/my_eval",
        bundle_url_mappings={"s3://my-bucket": "https://my-bucket.s3.amazonaws.com"},
    ),
    tasks=[FlowTask(name="task", model="openai/gpt-4o")],
)
```

After running this prints:
`Bundle URL: https://my-bucket.s3.amazonaws.com/bundles/my_eval`

Use this when storing bundles on cloud storage like S3 or on servers
with public HTTP access. Multiple mappings are applied in order.

Using Bundle URL maps makes sense along with the spec
[inheritance](defaults.qmd#inheritance) feature so you can configure the
same bundle mapping for all configs in a repository.

## Config Scripts

When loading a configuration file, Flow expects the last expression to
either be a `FlowSpec` or a function that returns a `FlowSpec`. Other
than this requirement, the configuration file may execute arbitrary
code.

### after_load

Configuration scripts are executed while loading the spec. At the time
that the script is running the spec is in an intermediate state
(includes may not have been processed, overrides not applied, and
template substitutions will not have run). To run code after the spec is
fully loaded a script can decorate a function with `@after_load`.

The decorated function may optionally implement the following arguments:

- `spec` - the fully loaded `FlowSpec`
- `files` - the list of configuration files that were loaded

One example of functionality that can be implemented using this feature
is validation code to enforce constraints. Instead of repeating this
validation code in every Flow configuration file, the code could be
placed in a `_flow.py` file that is auto included.

### Prevent Runs with Uncommitted Changes

Place a `_flow.py` file at your repository root to validate that all
configs are in clean git repositories. This validation runs
automatically for all configs in subdirectories.

**\_flow.py**

``` python
import subprocess
from pathlib import Path

from inspect_flow import after_load


def check_repo(path: str) -> None:
    abs_path = Path(path).resolve()
    check_dir = abs_path if abs_path.is_dir() else abs_path.parent

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=check_dir,
        capture_output=True,
        text=True,
        check=True,
    )

    if result.stdout.strip():
        raise RuntimeError(f"The repository at {check_dir} has uncommitted changes.")


@after_load
def validate_no_dirty_repo(files: list[str]) -> None:
    # Check no config files are in a dirty git repo
    for path in files:
        check_repo(path)
```

**config.py**

``` python
# Automatically inherits _flow.py
from inspect_flow import FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",
    tasks=[FlowTask(name="inspect_evals/gpqa_diamond", model="openai/gpt-4o")],
)
# Will fail if uncommitted changes exist in the repository
```

### Lock Config Fields

A `_flow.py` file can prevent configs from overriding critical settings:

**\_flow.py**

``` python
from inspect_flow import FlowOptions, FlowSpec, after_load

MAX_SAMPLES = 16


@after_load
def validate_max_samples(spec: FlowSpec) -> None:
    if not spec.options or not spec.options.max_samples == MAX_SAMPLES:
        raise ValueError("Do not override max_samples!")


FlowSpec(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
```

**config.py**

``` python
# Automatically inherits _flow.py
from inspect_flow import FlowOptions, FlowSpec, FlowTask

FlowSpec(
    log_dir="logs",
    options=FlowOptions(max_samples=32),  # Will raise ValueError!
    tasks=[FlowTask(name="inspect_evals/gpqa_diamond", model="openai/gpt-4o")],
)
```

This pattern is useful for enforcing organizational standards (resource
limits, safety constraints, etc.) across all evaluation configs in a
repository.
