from typing import Any

from inspect_ai.model import modelapi
from inspect_ai.model._providers.mockllm import MockLLM

instances: list[MockLLM] = []


@modelapi(name="editable-acme")
class EditableAcmeAPI(MockLLM):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        instances.append(self)
