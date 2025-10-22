import re
import subprocess
import tempfile
from pathlib import Path

from datamodel_code_generator import DataModelType, generate

from inspect_flow._types.flow_types import FlowConfig


def generate_typed_dict_code() -> list[str]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as tmp_file:
        generated_type_file = Path(tmp_file.name)

        generate(
            str(FlowConfig.model_json_schema()),
            output=generated_type_file,
            output_model_type=DataModelType.TypingTypedDict,
            custom_class_name_generator=lambda name: f"{name}Dict",
        )

        # Post-process the generated file to add union types
        with open(generated_type_file, "r") as f:
            lines = f.readlines()
    return lines


def modify_generated_code(lines: list[str]) -> list[str]:
    str_as_class = ["TaskConfig", "ModelConfig"]

    def replacement(m: re.Match[str]) -> str:
        if m.group(1) in str_as_class:
            return f'Union[str, "{m.group(1)}", "{m.group(0)}"]'
        else:
            return f'Union["{m.group(1)}", "{m.group(0)}"]'

    generated_code: list[str] = []
    section = "comment"
    for line in lines:
        if section == "comment":
            if line.strip().startswith("from"):
                section = "imports"
            else:
                generated_code.append(line)
        if section == "imports":
            if line.strip().startswith("class"):
                section = "classes"
            # Do not include imports
        if section == "classes":
            if line.strip().startswith("class"):
                # Don't modify import or class definition lines
                generated_code.append(line)
            else:
                # Replace ClassNameDict with ClassName | ClassNameDict
                modified_line = re.sub(
                    r"\b(\w+)Dict\b",
                    replacement,
                    line,
                )
                generated_code.append(modified_line)
    return generated_code


def write_generated_code(generated_code: list[str]) -> None:
    output_file = Path(__file__).parent / "flow_types.py"

    with open(output_file, "r") as f:
        lines = f.readlines()

    output_lines: list[str] = []
    section = "before"
    for line in lines:
        if section == "before":
            output_lines.append(line)
            if line.strip() == "# BEGIN GENERATED CODE":
                section = "generated"
                output_lines.extend(generated_code)
        if section == "generated":
            if line.strip() == "# END GENERATED CODE":
                section = "after"
        if section == "after":
            output_lines.append(line)

    with open(output_file, "w") as f:
        f.writelines(output_lines)
    subprocess.run(["ruff", "format", str(output_file)], check=True)


def main():
    lines = generate_typed_dict_code()
    generated_code = modify_generated_code(lines)
    write_generated_code(generated_code)


if __name__ == "__main__":
    main()
