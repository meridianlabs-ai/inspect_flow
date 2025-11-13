#!/usr/bin/env python3
"""Check that all items in __all__ have docstrings.

This script verifies that all publicly exported functions, classes, and
constants (listed in __all__) have docstrings, even if they're defined
in private modules.
"""

import ast
import sys
from pathlib import Path


def get_docstring(node: ast.AST) -> str | None:
    """Get the docstring from a function or class node."""
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
        return ast.get_docstring(node)
    return None


def find_definition(module_ast: ast.Module, name: str) -> ast.AST | None:
    """Find the definition of a name in a module AST."""
    for node in ast.walk(module_ast):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.name == name:
                return node
    return None


def resolve_import(
    module_path: Path, import_name: str, from_module: str
) -> tuple[Path | None, str]:
    """Resolve an import to its source file and name.

    Args:
        module_path: Path to the current module
        import_name: Name being imported
        from_module: Module it's imported from (e.g., 'inspect_flow._types.factories')

    Returns:
        Tuple of (source_file_path, original_name)
    """
    # Find the project root (where src/ is located)
    project_root = Path.cwd().resolve()
    src_dir = project_root / "src"

    if not src_dir.exists():
        return None, import_name

    # Convert module name to file path
    parts = from_module.split(".")

    # Skip 'inspect_flow' prefix if present
    if parts and parts[0] == "inspect_flow":
        parts = parts[1:]

    # Build path: src/inspect_flow/...
    target_path = src_dir / "inspect_flow"
    for part in parts:
        target_path = target_path / part

    # Try both .py file and __init__.py in directory
    py_file = target_path.with_suffix(".py")
    if py_file.exists():
        return py_file.resolve(), import_name

    init_file = target_path / "__init__.py"
    if init_file.exists():
        return init_file.resolve(), import_name

    return None, import_name


def check_module(module_path: Path) -> list[str]:
    """Check a module for missing docstrings on __all__ exports.

    Args:
        module_path: Path to the Python module to check

    Returns:
        List of error messages for missing docstrings
    """
    errors = []

    try:
        source = module_path.read_text()
        tree = ast.parse(source, filename=str(module_path))
    except Exception as e:
        return [f"{module_path}: Failed to parse: {e}"]

    # Find __all__ definition
    all_exports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        all_exports = [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant)
                            and isinstance(elt.value, str)
                        ]
                        break

    if not all_exports:
        return []  # No __all__, nothing to check

    # Track imports to resolve where names come from
    imports: dict[str, tuple[str, str]] = {}  # name -> (module, original_name)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imports[name] = (node.module, alias.name)

    # Check each export
    for export_name in all_exports:
        # Skip special variables
        if export_name.startswith("__"):
            continue

        # Check if it's imported
        if export_name in imports:
            from_module, original_name = imports[export_name]
            source_file, name_to_check = resolve_import(
                module_path, original_name, from_module
            )

            if source_file and source_file.exists():
                try:
                    source = source_file.read_text()
                    source_tree = ast.parse(source, filename=str(source_file))
                    definition = find_definition(source_tree, name_to_check)

                    if definition and not get_docstring(definition):
                        rel_path = source_file.relative_to(Path.cwd())
                        errors.append(
                            f"{module_path.relative_to(Path.cwd())}: '{export_name}' "
                            f"(defined in {rel_path}) is missing a docstring"
                        )
                except Exception as e:
                    errors.append(
                        f"{module_path}: Failed to check import '{export_name}': {e}"
                    )
        else:
            # It's defined locally
            definition = find_definition(tree, export_name)
            if definition and not get_docstring(definition):
                errors.append(
                    f"{module_path.relative_to(Path.cwd())}: '{export_name}' is missing a docstring"
                )

    return errors


def main() -> int:
    """Run docstring checks on all Python modules in src/."""
    src_dir = Path("src").resolve()
    if not src_dir.exists():
        print("Error: src/ directory not found", file=sys.stderr)
        return 1

    all_errors: list[str] = []

    # Check all Python files in src/
    for py_file in src_dir.rglob("*.py"):
        errors = check_module(py_file.resolve())
        all_errors.extend(errors)

    # Ignore specific types
    all_errors = [e for e in all_errors if e.find("'ApprovalPolicyConfigDict'") == -1]

    if all_errors:
        print("Missing docstrings on public API exports:\n", file=sys.stderr)
        for error in sorted(all_errors):
            print(f"  {error}", file=sys.stderr)
        print(
            f"\n{len(all_errors)} public API item(s) missing docstrings",
            file=sys.stderr,
        )
        return 1

    print("✓ All public API exports have docstrings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
