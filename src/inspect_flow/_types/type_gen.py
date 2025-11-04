import re
import subprocess
import tempfile
from copy import copy, deepcopy
from pathlib import Path
from typing import Any, Literal, TypeAlias

from datamodel_code_generator import DataModelType, InputFileType, generate

from inspect_flow._types.flow_types import _FlowConfig

GenType = Literal["Dict", "MatrixDict"]

# TODO:ransom private import
ADDITIONAL_IMPORTS = [
    "from __future__ import annotations\n",
    "from inspect_ai.model import BatchConfig, GenerateConfig, ResponseSchema\n",
    "from inspect_ai.util import JSONSchema, SandboxEnvironmentSpec\n",
    "from inspect_ai.approval._policy import ApprovalPolicyConfig, ApproverPolicyConfig\n",
    "from inspect_flow._types.flow_types import FlowAgent, FlowEpochs, FlowOptions, FlowModel, FlowSolver, FlowTask\n",
]

STR_AS_CLASS = ["FlowTask", "FlowModel", "FlowSolver", "FlowAgent"]

MATRIX_CLASS_FIELDS = {
    "FlowTask": ["args", "solver", "model", "config", "model_roles"],
    "FlowModel": ["config"],
    "FlowSolver": ["args"],
    "FlowAgent": ["args"],
    "GenerateConfig": [
        "system_message",
        "max_tokens",
        "top_p",
        "temperature",
        "stop_seqs",
        "best_of",
        "frequency_penalty",
        "presence_penalty",
        "logit_bias",
        "seed",
        "top_k",
        "num_choices",
        "logprobs",
        "top_logprobs",
        "parallel_tool_calls",
        "internal_tools",
        "max_tool_output",
        "cache_prompt",
        "reasoning_effort",
        "reasoning_tokens",
        "reasoning_summary",
        "reasoning_history",
        "response_schema",
        "extra_body",
    ],
}

Schema: TypeAlias = dict[str, Any]


def remove_none_option(any_of: list[Schema]) -> list[Schema]:
    return [v for v in any_of if v.get("type") != "null"]


def field_type_to_list(field_schema: Schema) -> None:
    field_type: Schema
    if "type" in field_schema:
        type = field_schema["type"]
        if type == "array":
            field_type = {"type": type, "items": field_schema["items"]}
            del field_schema["items"]
        else:
            field_type = {"type": type}
        del field_schema["type"]
    elif "anyOf" in field_schema:
        any_of: list[Schema] = field_schema["anyOf"]
        del field_schema["anyOf"]
        any_of = remove_none_option(any_of)
        field_type = {"anyOf": any_of}
    else:
        # Any type
        field_type = {}

    field_schema["anyOf"] = [{"type": "array", "items": field_type}, {"type": "null"}]
    if "default" not in field_schema:
        field_schema["default"] = None


def root_type_as_def(schema: Schema) -> None:
    defs: Schema = schema["$defs"]
    del schema["$defs"]
    root_type = copy(schema)
    schema.clear()
    defs[root_type["title"]] = root_type
    schema["$defs"] = defs


def create_matrix_dict(dict_def: Schema, title: str) -> None:
    properties: Schema = dict_def["properties"]
    for name, value in list(properties.items()):
        if name in MATRIX_CLASS_FIELDS[title]:
            field_type_to_list(value)
        else:
            del properties[name]


def create_type(defs: Schema, title: str, base_type: Schema, type: GenType) -> None:
    dict_def = deepcopy(base_type)
    dict_def.pop("required", None)
    if type == "MatrixDict":
        create_matrix_dict(dict_def, title)

    new_title = title + type
    if new_title.startswith("_"):
        new_title = new_title[1:]
    dict_def["title"] = new_title
    defs[new_title] = dict_def


def ignore_type(defs: Schema, title: str, ignore_type: Schema) -> None:
    del defs[title]
    new_title = "Ignore" + title
    ignore_type[title] = new_title
    defs[new_title] = ignore_type


def update_field_refs(field_schema: Schema, parent_list: list[Schema] | None) -> None:
    if "anyOf" in field_schema:
        any_of_list: list[Schema] = field_schema["anyOf"]
        for field in list(any_of_list):
            update_field_refs(field, any_of_list)
    if "items" in field_schema:
        items_def = field_schema["items"]
        update_field_refs(items_def, None)
    if "additionalProperties" in field_schema:
        additional_properties = field_schema["additionalProperties"]
        if isinstance(additional_properties, dict):
            update_field_refs(additional_properties, None)
    if "$ref" in field_schema:
        type: str = field_schema["$ref"]
        split = type.split("/")
        type_name = split[-1]
        split[-1] = "Ignore" + type_name
        ignore_ref = "/".join(split)
        split[-1] = type_name + "Dict"
        dict_ref = "/".join(split)
        field_schema["$ref"] = ignore_ref
        if parent_list:
            parent_list.append({"$ref": dict_ref})
            if type_name in STR_AS_CLASS:
                parent_list.append({"type": "string"})
        else:
            del field_schema["$ref"]
            field_schema["anyOf"] = [{"$ref": ignore_ref}, {"$ref": dict_ref}]
            if type_name in STR_AS_CLASS:
                field_schema["anyOf"].append({"type": "string"})


def update_refs(type_def: Schema) -> None:
    properties: Schema = type_def["properties"]
    for field_value in properties.values():
        update_field_refs(field_value, None)


def create_dict_types(schema: Schema) -> None:
    defs: Schema = schema["$defs"]
    for title, v in list(defs.items()):
        update_refs(v)
        create_type(defs, title, v, "Dict")
        if title in MATRIX_CLASS_FIELDS:
            create_type(defs, title, v, "MatrixDict")
        ignore_type(defs, title, v)


def generate_dict_code() -> list[str]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as tmp_file:
        generated_type_file = Path(tmp_file.name)

        schema = _FlowConfig.model_json_schema()
        root_type_as_def(schema)
        create_dict_types(schema)

        generate(
            str(schema),
            input_file_type=InputFileType.JsonSchema,
            output=generated_type_file,
            output_model_type=DataModelType.TypingTypedDict,
            use_generic_container_types=True,
            use_field_description=True,
            use_schema_description=True,
        )

        with open(generated_type_file, "r") as f:
            lines = f.readlines()
    return lines


def add_docstr_line(line: str, result: list[str]) -> None:
    indent = line[: len(line) - len(line.lstrip())]
    split = line.strip().split("\\n")
    result.extend([f"{indent}{li}\n" if li else "\n" for li in split])


def expand_docstring_newlines(lines: list[str]) -> list[str]:
    r"""Convert literal \\n in docstrings to actual newlines."""
    result: list[str] = []
    in_docstring = False

    for line in lines:
        stripped = line.strip()

        # Check if this line starts a docstring
        if not in_docstring and stripped.startswith('"""'):
            if not (stripped.endswith('"""') and len(stripped) >= 6):
                in_docstring = True
            add_docstr_line(line, result)
        elif in_docstring:
            if stripped.endswith('"""'):
                in_docstring = False
            add_docstr_line(line, result)
        else:
            result.append(line)

    return result


def convert_multiline_docstrings_to_single_line(lines: list[str]) -> list[str]:
    """Convert multi-line docstrings to single-line format when they contain only one line of text."""
    result: list[str] = []
    in_docstring = False
    docstring_lines: list[str] = []
    docstring_indent = ""
    original_lines = []

    for line in lines:
        stripped = line.strip()

        # Check if this line starts a docstring
        if not in_docstring and stripped.startswith('"""'):
            # Check if it's already a single-line docstring
            if stripped.endswith('"""') and len(stripped) > 6:
                result.append(line)
                continue
            # Start collecting a multi-line docstring
            in_docstring = True
            original_lines = [line]
            docstring_indent = line[: len(line) - len(line.lstrip())]
            docstring_lines = [stripped[3:]]  # Remove opening """
        elif in_docstring:
            # Check if this line ends the docstring
            if stripped.endswith('"""'):
                # Add the final content (without closing """)
                content = stripped[:-3].strip()
                if content:
                    docstring_lines.append(content)

                # Filter out empty lines
                non_empty_lines = [line for line in docstring_lines if line.strip()]

                # Only convert to single-line if there's exactly one line of content
                if len(non_empty_lines) == 1:
                    full_docstring = non_empty_lines[0].strip()
                    result.append(f'{docstring_indent}"""{full_docstring}"""\n')
                else:
                    result.extend(original_lines)
                    result.append(line)

                in_docstring = False
            else:
                # Continue collecting docstring content
                original_lines.append(line)
                docstring_lines.append(line)
        else:
            result.append(line)

    return result


def should_skip_class(line: str) -> bool:
    if line.find("Ignore") != -1:
        return True
    return False


def modify_generated_code(lines: list[str]) -> list[str]:
    generated_code: list[str] = [
        "# generated by type_gen.py (using datamodel-codegen)\n",
        "\n",
    ]
    section = "comment"
    for line in lines:
        if section == "comment":
            if line.strip().startswith("from"):
                section = "imports"
                generated_code.extend(ADDITIONAL_IMPORTS)
        elif section == "imports":
            if line.strip().startswith("class"):
                section = "classes"
            else:
                generated_code.append(line)
        elif section == "ignore class":
            if line.strip().startswith("class"):
                section = "classes"

        if section == "classes":
            if line.strip().startswith("class"):
                if should_skip_class(line):
                    section = "ignore class"
                else:
                    generated_code.append(line)
            else:
                # Replace IgnoreClassName with ClassName
                modified_line = re.sub(
                    r"\bIgnore(\w+)\b",
                    lambda m: m.group(1),
                    line,
                )
                generated_code.append(modified_line)

    # First pass: expand literal \n in docstrings to actual newlines
    generated_code = expand_docstring_newlines(generated_code)

    # Second pass: convert multi-line docstrings to single-line when they contain only one line
    generated_code = convert_multiline_docstrings_to_single_line(generated_code)

    return generated_code


def write_generated_code(file_name: str, generated_code: list[str]) -> None:
    output_file = Path(__file__).parent / file_name

    with open(output_file, "w") as f:
        f.writelines(generated_code)
    subprocess.run(["ruff", "check", "--fix", str(output_file)], check=True)
    subprocess.run(["ruff", "format", str(output_file)], check=True)


def main():
    lines = generate_dict_code()
    generated_code = modify_generated_code(lines)
    write_generated_code("dicts.py", generated_code)


if __name__ == "__main__":
    main()
