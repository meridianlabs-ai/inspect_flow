from inspect_flow._types.generated import (
    FlowAgent,
    FlowModel,
    FlowSolver,
    FlowTask,
    GenerateConfig,
)
from inspect_flow._types.merge import (
    merge,
    merge_recursive,
)


def test_merge():
    agent = merge(
        FlowAgent(
            name="base_agent",
            args={"temperature": 0.0},
            flow_metadata={"base": "agent"},
        ),
        FlowAgent(args={"temperature": 0.5}, flow_metadata={"add": "agent"}),
    )
    assert agent.name == "base_agent"
    assert agent.args
    assert agent.args["temperature"] == 0.5
    assert agent.flow_metadata
    assert agent.flow_metadata["base"] == "agent"
    assert agent.flow_metadata["add"] == "agent"

    config = merge(GenerateConfig(max_tokens=100), GenerateConfig(top_p=0.9))
    assert config.max_tokens == 100
    assert config.top_p == 0.9

    model = merge(
        FlowModel(
            name="base_model", role="mark", config=GenerateConfig(temperature=0.3)
        ),
        FlowModel(config=GenerateConfig(top_p=0.8), role="updated_mark"),
    )
    assert model.name == "base_model"
    assert model.role == "updated_mark"
    assert model.config
    assert model.config.temperature == 0.3
    assert model.config.top_p == 0.8

    solver = merge(FlowSolver(name="base_solver"), FlowSolver(args={"max_retries": 3}))
    assert solver.name == "base_solver"
    assert solver.args
    assert solver.args["max_retries"] == 3

    task = merge(
        FlowTask(
            name="base_task",
            config=GenerateConfig(timeout=30),
            flow_metadata={"base": "task", "both": "base"},
        ),
        FlowTask(
            config=GenerateConfig(max_retries=3),
            flow_metadata={"add": "task", "both": "add"},
        ),
    )
    assert task.name == "base_task"
    assert task.config
    assert task.config.timeout == 30
    assert task.config.max_retries == 3
    assert task.flow_metadata
    assert task.flow_metadata["base"] == "task"
    assert task.flow_metadata["add"] == "task"
    assert task.flow_metadata["both"] == "add"


def test_merge_none_does_not_override():
    """Test that None fields in add_dict do not override set fields in base_dict."""
    base_dict = {"name": "base_name", "temperature": 0.5, "max_tokens": 100}
    add_dict = {"temperature": None, "top_p": 0.9}

    result = merge_recursive(base_dict, add_dict)

    # None value in add_dict should not override the set value in base_dict
    assert result["name"] == "base_name"
    assert result["temperature"] == 0.5  # Should NOT be None
    assert result["max_tokens"] == 100
    assert result["top_p"] == 0.9
