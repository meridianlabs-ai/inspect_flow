from pathlib import Path

from inspect_flow._config.config import load_config
from inspect_flow._runner.run import run_eval_set


def _test_run_eval_set() -> None:
    config_path = Path(__file__).parent.parent / "examples" / "local.eval-set.yaml"
    config = load_config(str(config_path))
    run_eval_set(eval_set_config=config.run.task_groups[0].eval_set)
