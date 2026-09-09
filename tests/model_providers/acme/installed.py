from inspect_ai.model import modelapi
from inspect_ai.model._providers.mockllm import MockLLMAPI


@modelapi(name="acme-models")
class AcmeAPI(MockLLMAPI):
    pass


@modelapi(name="custom-acme")
class CustomAcmeAPI(MockLLMAPI):
    pass
