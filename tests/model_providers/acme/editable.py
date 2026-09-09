from inspect_ai.model import modelapi
from inspect_ai.model._providers.mockllm import MockLLM


@modelapi(name="editable-acme")
class EditableAcmeAPI(MockLLM):
    pass
