import re
import subprocess
import tempfile
from copy import copy, deepcopy
from pathlib import Path
from typing import Any, Literal, TypeAlias

from datamodel_code_generator import DataModelType, InputFileType, generate

from inspect_flow._types.flow_types import FlowConfig

GenType = Literal["Dict", "MatrixDict"]

# TODO:ransom private import
ADDITIONAL_IMPORTS = [
    "from __future__ import annotations\n",
    "from inspect_ai.model import BatchConfig, GenerateConfig, ResponseSchema\n",
    "from inspect_ai.util import JSONSchema, SandboxEnvironmentSpec\n",
    "from inspect_ai.approval._policy import ApprovalPolicyConfig, ApproverPolicyConfig\n",
    "from inspect_flow._types.flow_types import FlowAgent, FlowEpochs, FlowOptions, FlowModel, FlowSolver, FlowTask\n",
]

STR_AS_CLASS = ["FlowTask", "FlowModel", "FlowSolver"]

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


def properties_to_lists(type_def: Schema) -> None:
    properties: Schema = type_def["properties"]
    type_def.pop("required", None)
    for field_value in properties.values():
        field_type_to_list(field_value)


def root_type_as_def(schema: Schema) -> None:
    defs: Schema = schema["$defs"]
    del schema["$defs"]
    root_type = copy(schema)
    schema.clear()
    defs[root_type["title"]] = root_type
    schema["$defs"] = defs


def create_type(defs: Schema, title: str, base_type: Schema, type: GenType) -> None:
    dict_def = deepcopy(base_type)
    if type == "MatrixDict":
        properties_to_lists(dict_def)
    new_title = title + type
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
        create_type(defs, title, v, "MatrixDict")
        ignore_type(defs, title, v)


def generate_dict_code() -> list[str]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as tmp_file:
        generated_type_file = Path(tmp_file.name)

        schema = FlowConfig.model_json_schema()
        root_type_as_def(schema)
        create_dict_types(schema)

        generate(
            str(schema),
            input_file_type=InputFileType.JsonSchema,
            output=generated_type_file,
            output_model_type=DataModelType.TypingTypedDict,
            use_generic_container_types=True,
            use_field_description=False,
            use_schema_description=False,
        )

        with open(generated_type_file, "r") as f:
            lines = f.readlines()
    return lines


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
                if line.find("Ignore") != -1:
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
