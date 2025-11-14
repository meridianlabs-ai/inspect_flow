# Inspect Flow Internals

## _types Module

[_types](./_types) defines the types used in inspect flow configurations. 

[flow_config.py](./_types/flow_config.py) defines the pydantic types for the configuration. These types have a "Flow" prefix, e.g. `FlowTask`.

[type_gen.py](./_types/type_gen.py) defines the code generation logic that generates TypedDict classes based on the pydantic types.
These generated types are in [generated.py](./_types/generated.py).

`FlowTaskDict` and other types with a `Dict` suffix are TypedDicts corresponding to the Pydantic types.
These are used primarily to unpack kwargs in the _with functions.
`FlowTaskMatrixDict` and the other types with a `MatrixDict` suffix are TypedDicts that store lists instead of single values.
These are for use in the matrix functions with lists for their field types.

[factories.py](./_types/factories.py) defines three types of functions.
The `_with` functions apply fields to all objects in a list. For example `task_with` sets fields on a list of tasks (specified as a list of string, `FTask`, `FlowTask`, and `FlowTaskDict`).
The `_matrix` functions, like `tasks_matrix` generate lists of types from the product of lists of field values. 

## _api Module

[_api](./_api) defines the public API for inspect flow. 
This includes the main entry points for running flows and interacting with the framework.
These functions correspond to the CLI commands defined in the [_cli](./_cli) module.

## _cli Module

[_cli](./_cli) defines the command line interface for inspect flow. The main command is `run`, defined in [run.py](./_cli/run.py).

## _config Module

[_config](./_config) is responsible for loading and validating the flow configuration. The main function is `load_config`, defined in [config.py](./_config/config.py).

## _launcher Module

[_launcher](./_launcher) is responsible for creating the virtual environment, installing package dependencies, and starting the flow runner process.
The main function is `launch`, defined in [launch.py](./_launcher/launch.py).

## _runner Module

[_runner](./_runner) is responsible for running the flow tasks within the virtual environment.
The main function is `flow_run`, defined in [run.py](./_runner/run.py).
This involves:
1. Resolving the flow configuration into a canonical representation of the tasks with all defaults explicitly set.
This may require loading source files to determine the exported task functions.
2. Instantiating the tasks and all dependencies.
This converts from the configuration into the inspect AI objects required to run the tasks.
3. Running the tasks.
Currently eval_set is used, although this may change in the future.

## _util Module

[_util](./_util) defines utility functions and classes used throughout the inspect flow codebase.