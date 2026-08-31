import functools
import json
import os
from typing import Any

import pytest
import yaml
from inspect_ai import Task
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.tool import think
from inspect_ai.util import CheckpointConfig, Manual
from inspect_flow import FlowAgent, FlowModel, FlowOptions, FlowSpec, FlowTask
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._types.flow_types import not_given
from inspect_flow.api import dump_spec, load_spec, load_spec_data
from pydantic import ValidationError

from tests.local_eval.src.local_eval.noop import noop, sleep_for_solver


def test_round_trip_preserves_spec():
    spec = FlowSpec(
        log_dir="logs",
        env={"FOO": "bar"},
        tasks=[
            FlowTask(
                name="mod/task",
                model=FlowModel(
                    name="openai/gpt-4o", config=GenerateConfig(temperature=0.5)
                ),
                model_roles={"grader": "openai/gpt-4o-mini"},
            )
        ],
    )
    data = json.loads(json.dumps(dump_spec(spec)))
    assert load_spec_data(data) == spec


def test_round_trip_preserves_list_valued_model_role_order():
    # author order is canonical on the wire: inspect-ai's task_identifier
    # derives identity from declaration order, so sorting would silently
    # change which store entries a spec reuses
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="mod/task",
                model_roles={"grader": ["openai/b", FlowModel(name="openai/a")]},
            )
        ]
    )
    data = json.loads(json.dumps(dump_spec(spec)))
    assert data["tasks"][0]["model_roles"]["grader"] == [
        "openai/b",
        {"name": "openai/a"},
    ]
    assert load_spec_data(data) == spec


def test_load_rejects_empty_model_role_list():
    # inspect-ai's resolve_model_roles rejects an empty list at eval time;
    # reject it at the load boundary instead of after launch
    with pytest.raises(ValidationError):
        load_spec_data({"tasks": [{"name": "mod/task", "model_roles": {"grader": []}}]})


def test_dump_omits_unset_fields():
    assert dump_spec(FlowSpec(log_dir="logs")) == {"log_dir": "logs"}


def test_dump_never_contains_not_given_sentinel():
    spec = FlowSpec(log_dir="logs")
    spec.includes = not_given  # the loader assigns the sentinel explicitly
    data = dump_spec(spec)
    assert "NOT_GIVEN" not in json.dumps(data)


def test_dump_preserves_explicit_none():
    data = dump_spec(FlowSpec(store=None))
    assert data == {"store": None}
    loaded = load_spec_data(data)
    assert loaded.store is None
    assert "store" in loaded.model_fields_set


def test_dump_rejects_live_task():
    spec = FlowSpec(tasks=[Task(name="probe")])
    with pytest.raises(ValueError, match="Task"):
        dump_spec(spec)


def test_dump_rejects_live_object_in_args():
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="mod/task",
                model=FlowModel(name="m/m", model_args={"client": object()}),
            )
        ]
    )
    with pytest.raises(ValueError, match="cannot be represented in a portable spec"):
        dump_spec(spec)


def test_dump_encodes_registered_factory_as_registry_name():
    # a registered factory callable encodes to its registry name — the same
    # string a user would write as `factory="noop"`. Whether that name resolves
    # in another process depends on that process's environment, not on dump_spec
    spec = FlowSpec(tasks=[FlowTask(factory=noop)])
    data = dump_spec(spec)
    assert data["tasks"][0]["factory"] == "noop"
    loaded = load_spec_data(data)
    assert isinstance(loaded.tasks, list)
    assert isinstance(loaded.tasks[0], FlowTask)
    assert loaded.tasks[0].factory == "noop"


def test_dump_normalizes_unvalidated_assignment():
    # pydantic does not validate on assignment, so a coercible wrong-typed
    # value can sit in a typed field; the dump must be canonical anyway
    opts = FlowOptions()
    string_value: Any = "2.5"
    opts.retry_wait = string_value
    with pytest.warns(UserWarning, match="Pydantic serializer warnings"):
        data = dump_spec(FlowSpec(options=opts))
    assert data == {"options": {"retry_wait": 2.5}}
    assert dump_spec(load_spec_data(data)) == data


def test_dump_is_canonically_stable_with_normalizing_callable():
    # the general guarantee: a live callable normalizes to its name on reload,
    # so the reloaded spec is not object-equal to the original, but re-dumping
    # it reproduces the wire form exactly
    spec = FlowSpec(tasks=[FlowTask(factory=noop)])
    data = dump_spec(spec)
    assert dump_spec(load_spec_data(data)) == data


def test_dumped_file_reference_instantiates_without_prior_registration():
    # the portable pattern: a task referenced by a file path resolves in a
    # process that never imported it, proving dump/load carry a reconstructable
    # reference (registration in the submitting process is not required)
    fixture = os.path.abspath("tests/config/standalone_serialize_task.py")
    ref = f"{fixture}@standalone_serialize_task"
    spec = FlowSpec(tasks=[FlowTask(name=ref)])
    data = json.loads(json.dumps(dump_spec(spec)))
    loaded = load_spec_data(data)
    tasks = instantiate_tasks(loaded, base_dir=".")
    assert [t.task.name for t in tasks] == [ref]


def test_dump_rejects_unregistered_callable_factory():
    # an unregistered callable would encode as a file@name reference that the
    # runtime resolver cannot reconstruct (it looks up the registry), so reject
    def my_task() -> Task:  # pragma: no cover
        return Task(name="my_task")

    spec = FlowSpec(tasks=[FlowTask(factory=my_task)])
    with pytest.raises(ValueError, match="registry"):
        dump_spec(spec)


def test_dump_rejects_builtin_callable_factory():
    # builtins have no __code__; they must get the documented ValueError, not
    # an AttributeError from the preflight dump's fallback
    builtin: Any = len
    spec = FlowSpec(tasks=[FlowTask(factory=builtin)])
    with pytest.raises(ValueError, match="cannot be represented in a portable spec"):
        dump_spec(spec)


def test_dump_rejects_partial_factory():
    def make_task(name: str) -> Task:  # pragma: no cover
        return Task(name=name)

    spec = FlowSpec(tasks=[FlowTask(factory=functools.partial(make_task, "t"))])
    with pytest.raises(ValueError, match="cannot be represented in a portable spec"):
        dump_spec(spec)


def test_round_trips_resolved_example_spec():
    spec = load_spec("examples/agents_matrix.py")
    data = json.loads(json.dumps(dump_spec(spec)))
    loaded = load_spec_data(data)
    # live tools in agent args are encoded as registry references, so object
    # equality cannot hold; the wire form itself must be stable
    assert dump_spec(loaded) == data


def test_yaml_round_trip():
    spec = FlowSpec(log_dir="logs", tasks=[FlowTask(name="mod/task")], store=None)
    data = yaml.safe_load(yaml.dump(dump_spec(spec)))
    assert load_spec_data(data) == spec


def test_dump_encodes_registry_object_in_args():
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="mod/task",
                solver=FlowAgent(name="react", args={"tools": [think()]}),
            )
        ]
    )
    data = dump_spec(spec)
    tool = data["tasks"][0]["solver"]["args"]["tools"][0]
    assert tool["name"] == "think"
    assert load_spec_data(data) == load_spec_data(json.loads(json.dumps(data)))


def test_dump_rejects_live_model():
    spec = FlowSpec(tasks=[FlowTask(name="mod/task", model=get_model("mockllm/m"))])
    with pytest.raises(ValueError, match="Model"):
        dump_spec(spec)


def test_dump_rejects_live_registry_task_in_typed_field():
    # a @task-decorated object is a registry object, so it does not hit the
    # raw-Task fallback; it must still be rejected because its registry-dict
    # encoding cannot reload into the typed `tasks` field
    spec = FlowSpec(tasks=[noop()])
    with pytest.raises(ValueError, match=r"tasks\[0\]"):
        dump_spec(spec)


def test_dump_rejects_live_registry_solver_in_typed_field():
    spec = FlowSpec(tasks=[FlowTask(name="mod/task", solver=sleep_for_solver(1))])
    with pytest.raises(ValueError, match=r"tasks\[0\]"):
        dump_spec(spec)


def test_dump_rejects_non_reloadable_non_live_spec():
    # the reload check is general, not hardcoded to live objects: an invalid
    # CheckpointConfig value smuggled through SkipValidation also fails to
    # re-validate, so dump_spec must reject it and name the affected field
    # (untyped kwargs construct the deliberately invalid config without a cast)
    bad_checkpoint: dict[str, Any] = {"trigger": Manual(), "retention": 5}
    spec = FlowSpec(options=FlowOptions(checkpoint=CheckpointConfig(**bad_checkpoint)))
    with pytest.raises(ValueError, match=r"options"):
        dump_spec(spec)


def test_dump_allows_live_registry_object_in_args():
    # a registry object nested in an untyped args mapping reloads fine, so it
    # must NOT be rejected (regression guard for the tools-in-args path)
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="mod/task",
                solver=FlowAgent(name="react", args={"inner": sleep_for_solver(1)}),
            )
        ]
    )
    data = dump_spec(spec)
    assert load_spec_data(data) == load_spec_data(json.loads(json.dumps(data)))


def test_dump_rejects_not_given_inside_untyped_dict():
    spec = FlowSpec(log_dir="logs", flow_metadata={"oops": not_given})
    with pytest.raises(ValueError, match=r"flow_metadata\.oops"):
        dump_spec(spec)


def test_dump_rejects_user_value_shaped_like_sentinel():
    # a user value indistinguishable from the serialized NotGiven sentinel
    # cannot survive the wire; reject it at dump time rather than silently
    # dropping it on load
    spec = FlowSpec(log_dir="logs", flow_metadata={"type": "NOT_GIVEN"})
    with pytest.raises(ValueError, match=r"flow_metadata"):
        dump_spec(spec)


def test_dump_rejects_non_finite_float():
    # a non-finite float is not standards-compliant JSON, so it cannot be part
    # of the canonical wire representation
    spec = FlowSpec(options=FlowOptions(retry_wait=float("inf")))
    with pytest.raises(ValueError, match=r"options\.retry_wait"):
        dump_spec(spec)


def test_load_rejects_non_finite_float():
    # JSON/YAML parsers accept NaN/Infinity by default, so non-finite floats can
    # reach the load boundary; reject them symmetrically with dump_spec
    with pytest.raises(ValueError, match=r"options\.retry_wait"):
        load_spec_data({"options": {"retry_wait": float("nan")}})


def test_dump_rejects_non_finite_in_nested_typed_model():
    # JSON-mode serialization silently DROPS a non-finite float from nested
    # inspect-ai models (GenerateConfig(temperature=nan) dumps as config: {}),
    # so the original python values must be checked before serialization
    spec = FlowSpec(
        tasks=[FlowTask(name="m/t", config=GenerateConfig(temperature=float("nan")))]
    )
    with pytest.raises(ValueError, match=r"temperature"):
        dump_spec(spec)


def test_dump_rejects_non_finite_in_untyped_field():
    # in untyped mappings json-mode coerces nan to null; reject uniformly with
    # the typed-field cases rather than silently changing the value
    spec = FlowSpec(log_dir="l", flow_metadata={"x": float("nan")})
    with pytest.raises(ValueError, match=r"flow_metadata\.x"):
        dump_spec(spec)


def test_dump_rejects_numeric_string_coerced_to_non_finite():
    # symmetric with the load-side check: an unvalidated "1e999" in a nested
    # model coerces to inf during re-validation, after the pre-serialization
    # walk has already run; the verified spec's values must be checked too
    cfg = GenerateConfig(temperature=0.5)
    string_value: Any = "1e999"
    cfg.temperature = string_value
    spec = FlowSpec(tasks=[FlowTask(name="m/t", config=cfg)])
    with pytest.warns(UserWarning, match="Pydantic serializer warnings"):
        with pytest.raises(ValueError, match=r"temperature"):
            dump_spec(spec)


def test_dump_rejects_non_finite_inside_set():
    # a set is not a Sequence, so its members need explicit traversal; json
    # mode would otherwise coerce {nan} to [None] silently
    spec = FlowSpec(log_dir="l", flow_metadata={"x": {float("nan")}})
    with pytest.raises(ValueError, match=r"flow_metadata\.x"):
        dump_spec(spec)


def test_dump_rejects_iterator_value():
    # a single-use iterator cannot be dumped deterministically (serialization
    # consumes it, so a second dump of the same spec would differ) and its
    # members evade the non-finite walk
    spec = FlowSpec(log_dir="l", flow_metadata={"x": iter([1.0, 2.0])})
    with pytest.raises(ValueError, match=r"flow_metadata\.x.*iterator"):
        dump_spec(spec)


def test_dump_rejects_non_finite_mapping_key():
    # a non-finite float key nested in an untyped value would otherwise coerce
    # to the string "None" on the wire
    spec = FlowSpec(log_dir="l", flow_metadata={"x": {float("inf"): "v"}})
    with pytest.raises(ValueError, match=r"flow_metadata\.x"):
        dump_spec(spec)


def test_load_rejects_numeric_string_coerced_to_non_finite():
    # pydantic coerces a numeric string in a float field, so "1e999" becomes inf
    # only after the raw-data walk; the validated values must be checked too
    with pytest.raises(ValueError, match="non-finite"):
        load_spec_data({"options": {"retry_wait": "1e999"}})


def test_load_rejects_not_given_sentinel():
    data = {
        "tasks": [
            {
                "name": "mod/task",
                "model": {"name": "m/m", "model_args": {"type": "NOT_GIVEN"}},
            }
        ]
    }
    with pytest.raises(ValueError, match=r"tasks\[0\]\.model\.model_args"):
        load_spec_data(data)


def test_load_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        load_spec_data({"bogus": 1})
