from typing import Any

from inspect_ai.model import ModelAPI, modelapi
from inspect_ai.model._providers.mockllm import MockLLM

instances: list[MockLLM] = []
factory_calls: list[str] = []


class AcmeAPI(MockLLM):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        instances.append(self)


@modelapi(name="editable-acme")
class EditableAcmeAPI(AcmeAPI):
    pass


@modelapi(name="acme-models")
class NamedAcmeAPI(AcmeAPI):
    pass


@modelapi(name="lazy-acme")
def lazy_acme() -> type[ModelAPI]:
    factory_calls.append("lazy-acme")
    return AcmeAPI
