from pathlib import Path

from inspect_flow._config.config import load_config


def test_load_simple_eval_set() -> None:
    # Load the config file
    config_path = Path(__file__).parent.parent / "examples" / "simple.eval-set.yaml"
    config = load_config(str(config_path))

    # Verify the result
    assert config is not None
    assert config.run is not None
    assert len(config.run.task_groups) == 1
    task_group = config.run.task_groups[0]
    assert task_group.eval_set is not None
    assert len(task_group.eval_set.tasks) == 1
    assert task_group.eval_set.models is not None
    assert len(task_group.eval_set.models) == 1
