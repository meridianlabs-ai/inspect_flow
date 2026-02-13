from inspect_ai.model import GenerateConfig
from inspect_flow import FlowOptions, FlowSpec, configs_matrix, tasks_matrix
from inspect_flow._types.flow_types import FlowDependencies

FlowSpec(
    log_dir="./logs/display_test",
    log_dir_create_unique=False,
    options=FlowOptions(limit=1, retry_wait=1, retry_attempts=2),
    dependencies=FlowDependencies(
        additional_dependencies=[
            "../local_eval",
        ]
    ),
    tasks=tasks_matrix(
        task=[
            "local_eval/noop",  # task from a package
            "../local_eval/src/local_eval/noop.py@noop",  # task from a file relative to the config
        ],
        model=["mockllm/mock-llm1", "mockllm/mock-llm2"],
        config=configs_matrix(
            config=GenerateConfig(temperature=0),
            reasoning_effort=["none", "medium", "high"],
            max_tokens=[5, 10],
            frequency_penalty=[0, 1],
            best_of=[1, 3],
            presence_penalty=[0, 1],
            system_message=[
                None,
                "You are a helpful assistant. Answer questions to the best of your ability. And always answer in a sarcastic tone. And be concise. And use lots of emojis. And use internet slang. And make jokes. And be creative. And be funny. And be clever. And be witty. And be humorous. And be entertaining. And be engaging. And be interesting.",
            ],
        ),
    ),
)
