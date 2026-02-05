# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Prefer the shortest readable code that accomplishes the task. Think hard to optimize for clarity and maintainability.

DO use internal private functions from inspect-ai. DO NOT re-implement functionality that already exists in inspect-ai.

## Project Overview

Workflow orchestration for [Inspect AI](https://inspect.aisi.org.uk/) that enables you to run evaluations at scale with repeatability and maintainability.

Inspect Flow provides:

- **Declarative Configuration**: Define complex evaluations with tasks, models, and parameters in type-safe schemas
- **Repeatable & Shareable**: Encapsulated definitions of tasks, models, configurations, and Python dependencies ensure experiments can be reliably repeated and shared
- **Powerful Defaults**: Define defaults once and reuse them everywhere with automatic inheritance
- **Parameter Sweeping**: Matrix patterns for systematic exploration across tasks, models, and hyperparameters

Inspect Flow is designed for researchers and engineers running systematic AI evaluations who need to scale beyond ad-hoc scripts.

## Key Modules

- [_types](src/inspect_flow/_types) defines the types used in inspect flow configurations.
- [_api](src/inspect_flow/_api) defines the public API for inspect flow.
- [_cli](src/inspect_flow/_cli) defines the command line interface for inspect flow. The main command is `run`, defined in [run.py](src/inspect_flow/_cli/run.py).
- [_config](src/inspect_flow/_config) is responsible for loading and validating the flow configuration. The main function is `load_config`, defined in [config.py](src/inspect_flow/_config/config.py).
- [_launcher](src/inspect_flow/_launcher) is responsible for creating the virtual environment, installing package dependencies, and starting the flow runner process. The main function is `launch`, defined in [launch.py](src/inspect_flow/_launcher/launch.py).
- [_runner](src/inspect_flow/_runner) is responsible for running the flow tasks either inproc or within the virtual environment. The main function is `flow_run`, defined in [run.py](src/inspect_flow/_runner/run.py).
- [_util](src/inspect_flow/_util) defines utility functions and classes used throughout the inspect flow codebase.

## Build/Lint/Test Commands
- Repo setup: `uv sync`
- Run all tests: `pytest`
- Run a single test: `pytest tests/path/to/test_file.py::test_function_name -v`
- Format code: `ruff format`
- Lint code: `ruff check --fix`
- Type check: `pyright`

## Code Style Guidelines
- **Formatting**: Follow Google style convention. Use ruff for formatting
- **Imports**: Use isort order (enforced by ruff). Always place imports at the top of the file, not inside functions.
- **Types**: Strict typing is required. All functions must have type annotations
- **Naming**: Use snake_case for variables, functions, methods; PascalCase for classes
- **Docstrings**: Google-style docstrings required for public APIs. No docstrings for private/internal functions. Never write docstrings that describe implementation details—these duplicate the code and become stale when the code changes.
- **Comments**: Prefer self-documenting code to comments. Use comments to explain why, not what, and only when complex. Do not add comments that merely restate what the code does.
- **Error Handling**: Use appropriate exception types; include context in error messages. Avoid try/except blocks unless absolutely necessary—if you add one, include a test that exercises that code path.
- **Testing**: Write tests with pytest; maintain high coverage
- **Bug Fixes**: Include a test that reproduces the bug before fixing it
- **Pull Requests**: Keep PRs small and focused. Include a description of changes and rationale. Use conventional commit messages ("fix:" and "feat:").

Respect existing code patterns when modifying files. Run linting before committing changes.