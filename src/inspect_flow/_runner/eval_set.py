from __future__ import annotations

from inspect_ai import Task
from inspect_ai import eval_set as inspect_eval_set
from inspect_ai.log import EvalLog
from inspect_ai.util import DisplayType
from inspect_ai.util._display import init_display_type

from inspect_flow._display.display import get_display_type
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.scanner import resolve_scanner
from inspect_flow._types.after_instantiate import run_after_instantiate_hooks
from inspect_flow._types.flow_types import FlowInternal, FlowOptions, FlowSpec
from inspect_flow._util.list_util import sequence_to_list
from inspect_flow._util.logging import get_last_log_level, update_log_level
from inspect_flow._util.module_util import execute_file_and_get_last_result
from inspect_flow._util.not_given import default, default_none
from inspect_flow._util.path_util import cwd_relative_path


def eval_set_for_spec(spec: FlowSpec, base_dir: str) -> tuple[bool, list[EvalLog]]:
    """Resolve a spec, instantiate its tasks, and make its `eval_set()` call.

    This is the bare spec -> `eval_set()` path with none of the surrounding
    `flow run` behavior: no flow.yaml is written, no store is consulted, and
    no log directory scanning or result display occurs.

    Args:
        spec: The (expanded) flow spec.
        base_dir: The base directory for resolving relative paths.
    """
    resolved_spec = resolve_spec(spec, base_dir=base_dir)
    options = resolved_spec.options or FlowOptions()
    display_type = options.display or get_display_type()
    init_display_type(display_type)
    log_level = options.log_level or get_last_log_level()

    if not resolved_spec.log_dir:
        raise ValueError("log_dir must be set before running the flow spec")

    load_preload_files(resolved_spec)
    tasks = instantiate_tasks(resolved_spec, base_dir=base_dir)
    eval_tasks = run_after_instantiate_hooks([t.task for t in tasks])
    update_log_level(log_level)
    return eval_set_call(
        resolved_spec,
        options,
        eval_tasks,
        display_type=display_type,
        log_level=log_level,
    )


def load_preload_files(spec: FlowSpec) -> None:
    # Executes the Python files listed in spec.internal.preload_files for
    # their side effects (e.g. registering @after_instantiate decorators).
    # Effectively a no-op inproc (the parent already loaded these); for venv
    # subprocesses, this is the bridge that carries side-effect registrations
    # across the parent → child boundary.
    internal = spec.internal
    if not isinstance(internal, FlowInternal):
        return
    files = internal.preload_files
    if not files:
        return
    for file_path in files:
        execute_file_and_get_last_result(file_path, args={})


def eval_set_call(
    resolved_spec: FlowSpec,
    options: FlowOptions,
    tasks: list[Task],
    display_type: DisplayType | None,
    log_level: str | None,
) -> tuple[bool, list[EvalLog]]:
    """The single `eval_set()` boundary call for a resolved spec (the one place where `FlowOptions` maps to `eval_set()` arguments)."""
    assert resolved_spec.log_dir
    return inspect_eval_set(
        tasks=tasks,
        log_dir=cwd_relative_path(resolved_spec.log_dir),
        retry_attempts=default_none(options.retry_attempts),
        retry_wait=default_none(options.retry_wait),
        retry_connections=default_none(options.retry_connections),
        retry_cleanup=default_none(options.retry_cleanup),
        # model= FlowTask
        # model_base_url= FlowModel
        # model_args= FlowModel
        # model_roles= FlowTask
        # task_args= FlowTask
        sandbox=default_none(options.sandbox),
        sandbox_cleanup=default_none(options.sandbox_cleanup),
        checkpoint=default_none(options.checkpoint),
        acp_server=default_none(options.acp_server),
        ctl_server=default_none(options.ctl_server),
        # solver= FlowTask
        scanner=resolve_scanner(default_none(options.scanner)),
        tags=sequence_to_list(default_none(options.tags)),
        metadata=default_none(options.metadata),
        trace=default_none(options.trace),
        display=default_none(display_type),
        approval=default_none(options.approval),
        notification=default_none(options.notification),
        score=default(options.score, True),
        score_display=default_none(options.score_display),
        log_level=default_none(log_level),
        log_level_transcript=default_none(options.log_level_transcript),
        log_format=default_none(options.log_format),
        limit=default_none(options.limit),
        # sample_id= FlowTask
        sample_shuffle=default_none(options.sample_shuffle),
        # epochs= FlowTask
        fail_on_error=default_none(options.fail_on_error),
        continue_on_fail=default_none(options.continue_on_fail),
        retry_on_error=default(options.retry_on_error, 3),
        score_on_error=default_none(options.score_on_error),
        debug_errors=default_none(options.debug_errors),
        # message_limit= FlowTask
        # token_limit= FlowTask
        # turn_limit= FlowTask
        # time_limit= FlowTask
        # working_limit= FlowTask
        # cost_limit= FlowTask
        model_cost_config=default_none(options.model_cost_config),
        max_samples=default_none(options.max_samples),
        max_dataset_memory=default_none(options.max_dataset_memory),
        max_tasks=default(options.max_tasks, 10),
        max_subprocesses=default_none(options.max_subprocesses),
        max_sandboxes=default_none(options.max_sandboxes),
        log_samples=default_none(options.log_samples),
        log_realtime=default_none(options.log_realtime),
        log_images=default_none(options.log_images),
        log_model_api=default_none(options.log_model_api),
        log_refusals=default_none(options.log_refusals),
        log_buffer=default_none(options.log_buffer),
        log_shared=default_none(options.log_shared),
        bundle_dir=default_none(options.bundle_dir),
        bundle_overwrite=default(options.bundle_overwrite, False),
        log_dir_allow_dirty=default_none(options.log_dir_allow_dirty),
        eval_set_id=default_none(options.eval_set_id),
        embed_viewer=default(options.embed_viewer, False),
        retry_immediate=True,
        # kwargs= FlowSpec, FlowTask, and FlowModel allow setting the generate config
    )
