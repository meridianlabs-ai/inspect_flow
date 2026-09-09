from inspect_ai.model import modelapi
from inspect_ai.model._providers.mockllm import MockLLM


@modelapi(name="acme-models")
class AcmeAPI(MockLLM):
    pass


@modelapi(name="custom-acme")
class CustomAcmeAPI(MockLLM):
    pass
