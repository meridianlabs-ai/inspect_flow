# Running Flows


Once you’ve defined your Flow configuration, you can execute evaluations
using the `flow run` command. Flow also provides tools for previewing
configurations and controlling runtime behavior.

## The `flow run` Command

Execute your evaluation workflow:

``` bash
flow run config.py
```

**What happens when you run this:**

1.  Flow loads your configuration file
2.  Resolves all defaults and matrix expansions
3.  Searches the Flow Store for existing logs to reuse
4.  Executes evaluations via Inspect AI’s `eval_set()` in the current
    Python process
5.  Stores logs in `log_dir`
6.  Adds logs to the Flow Store and generates `flow-requirements.txt`

> [!TIP]
>
> ### Virtual Environment Mode
>
> For reproducible evaluation runs, you can use [virtual environment
> mode](advanced.qmd#virtual-environment-mode) which automatically
> creates an isolated environment and installs dependencies:
>
> ``` bash
> flow run matrix.py --venv
> ```
>
> Or set `execution_type="venv"` in your `FlowSpec`. Virtual environment
> mode automatically installs packages based on your config (e.g.,
> `model="openai/gpt-4"` installs `openai`) and dependency files, making
> it easy to share workflows with others. See [Execution
> Modes](advanced.qmd#execution-modes) to learn more.

### Common CLI Flags

**Preview without running:**

``` bash
flow run config.py --dry-run
```

Performs the full setup process and shows what would run:

- Applies all defaults and expands all matrix functions
- Instantiates tasks from the registry
- Checks for existing logs (in log directory and Flow Store)
- Shows which tasks would run and which logs would be reused
- Stops before actually running evaluations

This is invaluable for debugging what will actually run in your
evaluations.

**Override log directory:**

``` bash
flow run config.py --log-dir ./experiments/baseline
```

Changes where logs and results are stored.

**Runtime overrides:**

``` bash
flow run config.py \
  --set options.limit=100 \
  --set defaults.config.temperature=0.5
```

Override any configuration value at runtime. See [CLI
Overrides](defaults.qmd#cli-overrides) for more details.

## The `flow config` Command

Preview your configuration before running:

``` bash
flow config config.py
```

Displays the expanded configuration as YAML (applies defaults, includes,
and CLI overrides). Does not instantiate tasks or check for existing
logs—it only loads and expands the configuration file.

> [!TIP]
>
> ### When to Use Each Command
>
> - **`flow config`** - View expanded config as YAML, quick syntax check
> - **`flow run --dry-run`** - Preview what would run, check which logs
>   would be reused
> - **`flow run`** - Execute evaluations

## Running from Python

You can run Flow evaluations programmatically using the Python API:

**run.py**

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

The `inspect_flow.api` module provides programmatic access to Flow
capabilities. Key functions include:

- **`run()`** - Execute a Flow spec with full environment setup
  (equivalent to `flow run`)
- **`load_spec()`** - Load a Flow configuration from a Python file into
  a `FlowSpec` object
- **`config()`** - Get the expanded configuration as YAML (applies
  defaults, includes, overrides - equivalent to `flow config`)
- **`init()`** - Initialize Flow session settings (logging, display,
  .env loading)
- **`store_get()`** - Get a FlowStore instance for programmatic store
  access

See the [API Reference](reference/inspect_flow.api.qmd) for complete
documentation.

## Results and Logs

### Logs Directory

Evaluation results are stored in the `log_dir`:

    logs/
    ├── 2025-11-21T17-38-20+01-00_gpqa-diamond_KvJBGowidXSCLRhkKQbHYA.eval
    ├── 2025-11-21T17-38-20+01-00_mmlu-0-shot_Vnu2A3M2wPet5yobLiCQmZ.eval
    ├── .eval-set-id
    ├── eval-set.json
    ├── flow.yaml
    ├── flow-requirements.txt
    └── ...

**Directory structure:**

- Flow passes the `log_dir` directly to Inspect AI `eval_set()` for
  evaluation log storage
- Inspect AI handles the actual evaluation log file naming and storage
- Log file naming conventions follow Inspect AI’s standards (see
  [Inspect AI logging
  docs](https://inspect.aisi.org.uk/eval-logs.html#log-file-name))
- Flow automatically saves the resolved configuration as `flow.yaml` in
  the log directory
- Flow saves a snapshot of installed packages as
  `flow-requirements.txt`:
  - In **venv mode**: captures packages installed in the isolated
    environment
  - In **inproc mode**: captures packages from your current environment
- The `.eval-set-id` file contains the eval set identifier
- The `eval-set.json` file contains eval set metadata

> [!NOTE]
>
> Logs in this directory are automatically tracked by the [Flow
> Store](store.qmd), enabling log reuse across future runs.

**Log formats:**

- `.eval` - Binary Inspect AI log format (default, high-performance)
- `.json` - JSON format (if `log_format="json"` in `FlowOptions`)

### Viewing Results

**Using [Inspect View](https://inspect.aisi.org.uk/log-viewer.html):**

``` bash
inspect view
```

Opens the Inspect AI viewer to explore evaluation logs interactively.
[Inspect View](https://inspect.aisi.org.uk/log-viewer.html) can
automatically detect Flow config files in the log directory and render
them in the UI, making it easier to review the spec for the evaluations.

Click the Flow icon in the top right hand corner to view the Flow
config.

![Eval list rendered by Inspect View](images/inspect_view_list.png)

The Flow config file is rendered in YAML format.

![Flow config rendered by Inspect
View](images/inspect_view_flow_config.png)

### S3 Support

Store logs directly to S3:

``` python
FlowSpec(
    log_dir="s3://my-bucket/experiments/baseline",
    tasks=[...]
)
```

For more information on configuring an S3 bucket as a logs directory,
refer to the Inspect AI
[documentation](https://inspect.aisi.org.uk/eval-logs.html#sec-amazon-s3).
