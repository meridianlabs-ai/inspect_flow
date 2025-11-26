import yaml

from inspect_flow._types.flow_types import FlowJob


def config_to_yaml(job: FlowJob) -> str:
    return yaml.dump(
        job.model_dump(
            mode="json",
            exclude_unset=True,
            exclude_defaults=True,  # Must exclude_defaults so that NotGiven fields are not serialized
            # do not exclude_none, as for NotGiven fields they are significant
        ),
        default_flow_style=False,
        sort_keys=False,
    )
