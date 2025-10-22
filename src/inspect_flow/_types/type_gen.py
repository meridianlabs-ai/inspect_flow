import json
import re
from pathlib import Path

from datamodel_code_generator import DataModelType, generate

from inspect_flow._types.flow_types import FlowConfig, Matrix


def json_schema() -> str:
    schemas = {}
    for model in [FlowConfig, Matrix]:
        schema = model.model_json_schema()
        schemas.update(schema.get("$defs", {}))
    return json.dumps({"$defs": schemas, "type": "object"})


def main():
    output = Path(__file__).parent / "flow_type_dicts.py"

    generate(
        str(FlowConfig.model_json_schema()),
        output=output,
        output_model_type=DataModelType.TypingTypedDict,
        custom_class_name_generator=lambda name: f"{name}Dict",
    )

    # Post-process the generated file to add union types
    with open(output, "r") as f:
        lines = f.readlines()

    modified_lines = []
    for line in lines:
        if line.strip().startswith(("from", "class")):
            # Don't modify import or class definition lines
            modified_lines.append(line)
        else:
            # Replace ClassNameDict with ClassName | ClassNameDict
            modified_line = re.sub(
                r"\b(\w+)Dict\b",
                lambda m: f'Union["{m.group(1)}", {m.group(0)}]',
                line,
            )
            modified_lines.append(modified_line)

    with open(output, "w") as f:
        f.writelines(modified_lines)


if __name__ == "__main__":
    main()
