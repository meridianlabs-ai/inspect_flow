from pathlib import Path
from unittest.mock import patch

from inspect_ai import Task
from inspect_ai.model import GenerateConfig, Model
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.types import (
    FlowConfig,
    FlowOptions,
    Matrix,
    ModelConfig,
    TaskConfig,
)

from .test_helpers.log_helpers import init_test_logs, verify_test_logs

task_file = (
    Path(__file__).parent.parent
    / "examples"
    / "local_eval"
    / "src"
    / "local_eval"
    / "noop.py"
)


def test_task_with_get_model() -> None:
    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            config=FlowConfig(
                options=FlowOptions(log_dir="get_model"),
                matrix=Matrix(
                    models=[ModelConfig(name="mockllm/mock-llm")],
                    tasks=[
                        TaskConfig(
                            name="task_with_get_model", file=str(task_file.absolute())
                        )
                    ],
                ),
            )
        )

        mock_eval_set.assert_called_once()
        call_args = mock_eval_set.call_args
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)


# def test_task_with_two_models() -> None:
#     # This test verifies that the tasks have distinct identifiers and eval_set runs correctly
#     # So can not use a mock
#     log_dir = init_test_logs()

#     eval_set_config = EvalSetConfig(
#         tasks=[
#             PackageConfig(
#                 name="local_eval",
#                 file=str(task_file.absolute()),
#                 # package="local_eval",
#                 items=[TaskConfig(name="noop")],
#             )
#         ],
#         log_dir=log_dir,
#         models=[
#             PackageConfig(
#                 name="mockllm",
#                 package="mockllm",
#                 items=[ModelConfig(name="mock-llm1")],
#             ),
#             PackageConfig(
#                 name="mockllm",
#                 package="mockllm",
#                 items=[ModelConfig(name="mock-llm2")],
#             ),
#         ],
#     )

#     run_eval_set(eval_set_config=eval_set_config)

#     verify_test_logs(eval_set_config, log_dir)


# def test_model_generate_config() -> None:
#     system_message = "Test System Message"
#     with patch("inspect_ai.eval_set") as mock_eval_set:
#         run_eval_set(
#             eval_set_config=EvalSetConfig(
#                 tasks=[
#                     PackageConfig(
#                         name="local_eval",
#                         file=str(task_file.absolute()),
#                         items=[TaskConfig(name="noop")],
#                     )
#                 ],
#                 log_dir="get_model",
#                 models=[
#                     PackageConfig(
#                         name="mockllm",
#                         package="mockllm",
#                         items=[
#                             ModelConfig(
#                                 name="mock-llm",
#                                 args=GetModelArgs(
#                                     config=GenerateConfig(system_message=system_message)
#                                 ),
#                             )
#                         ],
#                     )
#                 ],
#             )
#         )

#         mock_eval_set.assert_called_once()
#         call_args = mock_eval_set.call_args
#         tasks_arg = call_args.kwargs["tasks"]
#         assert len(tasks_arg) == 1
#         assert isinstance(tasks_arg[0], Task)
#         assert isinstance(tasks_arg[0].model, Model)
#         config = tasks_arg[0].model.config
#         assert config.system_message == system_message
