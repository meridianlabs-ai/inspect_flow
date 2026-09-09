from inspect_ai.model import modelapi
from inspect_ai.model._providers.mockllm import MockLLMAPI


@modelapi(name="editable-acme")
class EditableAcmeAPI(MockLLMAPI):
    pass
