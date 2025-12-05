from inspect_flow import FlowJob, FlowModel, tasks_matrix

# Define models with metadata about capabilities
models = [
    FlowModel(name="openai/gpt-4o", flow_metadata={"context_window": 128000}),
    FlowModel(name="openai/gpt-4o-mini", flow_metadata={"context_window": 128000}),
    FlowModel(
        name="anthropic/claude-3-5-sonnet", flow_metadata={"context_window": 200000}
    ),
]

# Filter to only long-context models
long_context_models = [
    m for m in models if (m.flow_metadata or {}).get("context_window", 0) >= 128000
]

FlowJob(
    log_dir="logs",
    tasks=tasks_matrix(
        task="long_context_task",
        model=long_context_models,
    ),
)
