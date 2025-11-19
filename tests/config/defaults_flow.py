from inspect_flow import FlowDefaults, FlowJob, FlowModel

FlowJob(
    defaults=FlowDefaults(
        model=FlowModel(name="mockllm/mock-llm1", model_args={"mock_model_arg": 3})
    )
)
