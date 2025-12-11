from inspect_flow import FlowSpec
from inspect_flow._types.flow_types import FlowDependencies

FlowSpec(
    dependencies=FlowDependencies(
        additional_dependencies=[
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
        ]
    ),
)
