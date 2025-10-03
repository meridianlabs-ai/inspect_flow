from pathlib import Path

from inspect_flow._config.config import load_config


def test_load_simple_eval_set() -> None:
    # Load the config file
    config_path = Path(__file__).parent.parent / "examples" / "simple.eval-set.yaml"
    config = load_config(str(config_path))

    # Verify the result
    assert config is not None
    # TODO: Add specific assertions once types are finalized
