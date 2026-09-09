import sys

from inspect_ai.model import ModelAPI, get_model, modelapi
from inspect_ai.model._providers.mockllm import MockLLM
from inspect_flow import FlowSpec, FlowTask
from inspect_flow._launcher.auto_dependencies import collect_auto_dependencies
from inspect_flow._launcher.pip_string import get_pip_string

registered_name, expected_package = sys.argv[1:]


@modelapi(name=registered_name)
def provider() -> type[ModelAPI]:
    return MockLLM


model = f"{registered_name.split('/')[-1]}/example"
spec = FlowSpec(tasks=[FlowTask(model=model)])
assert collect_auto_dependencies(spec) == [get_pip_string(expected_package)]
assert isinstance(get_model(model).api, MockLLM)
