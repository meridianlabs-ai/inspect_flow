import sys

import inspect_ai._util.entrypoints as entrypoints
from inspect_flow import FlowSpec, FlowTask
from inspect_flow._launcher.auto_dependencies import collect_auto_dependencies
from inspect_flow._launcher.pip_string import get_pip_string

assert not entrypoints._inspect_ai_eps_loaded_all
assert "local_eval" not in sys.modules

for model, expected in [
    ("openai/gpt-4o", [get_pip_string("openai")]),
    ("none/none", []),
]:
    spec = FlowSpec(tasks=[FlowTask(model=model)])
    assert collect_auto_dependencies(spec) == expected
    assert not entrypoints._inspect_ai_eps_loaded_all
    assert "local_eval" not in sys.modules
