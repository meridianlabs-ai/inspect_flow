from inspect_flow import (
    FlowAgent,
    FlowDefaults,
    FlowJob,
    FlowModel,
    FlowSolver,
    FlowTask,
    GenerateConfig,
)

FlowJob(
    defaults=FlowDefaults(
        config=GenerateConfig(  # <1>
            max_connections=10,  # <1>
        ),  # <1>
        model=FlowModel(  # <2>
            model_args={"arg": "foo"},  # <2>
        ),  # <2>
        model_prefix={  # <3>
            "openai/": FlowModel(  # <3>
                config=GenerateConfig(  # <3>
                    max_connections=20  # <3>
                ),  # <3>
            ),  # <3>
        },  # <3>
        solver=FlowSolver(name="generate"),  # <4>
        solver_prefix={"chain_of_thought": FlowSolver(name="chain_of_thought")},  # <5>
        agent=FlowAgent(name="basic"),  # <6>
        agent_prefix={"inspect/": FlowAgent(name="inspect/basic")},  # <7>
        task=FlowTask(model="openai/gpt-4o"),  # <8>
        task_prefix={"inspect_evals/": FlowTask(model="openai/gpt-4o-mini")},  # <9>
    ),
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="openai/gpt-4o",
        )
    ],
)
