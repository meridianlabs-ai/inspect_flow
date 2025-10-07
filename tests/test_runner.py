from pathlib import Path

from inspect_flow._config.config import load_config
from inspect_flow._runner.runner import run


def _test_run_environment() -> None:
    config_path = Path(__file__).parent.parent / "examples" / "simple.eval-set.yaml"
    config = load_config(str(config_path))
    run(task_group=config.run.task_groups[0])
