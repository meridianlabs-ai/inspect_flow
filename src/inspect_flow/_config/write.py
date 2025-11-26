import yaml

from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.args import MODEL_DUMP_ARGS


def config_to_yaml(job: FlowJob) -> str:
    return yaml.dump(
        job.model_dump(**MODEL_DUMP_ARGS),
        default_flow_style=False,
        sort_keys=False,
    )
