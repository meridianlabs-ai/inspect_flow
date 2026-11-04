# Contributing to Inspect Flow

Thanks for contributing to Inspect Flow! This guide covers local setup, the checks
we run, and how commits and releases work.

## Development setup

Inspect Flow requires Python 3.11 or later. Clone the repository and sync the
environment:

```bash
git clone https://github.com/meridianlabs-ai/inspect_flow
cd inspect_flow
uv sync
source .venv/bin/activate
```

`uv sync` creates `.venv` with the exact versions in `uv.lock` and installs Flow
editable. The default `dev` dependency group brings in the `dev` extra (the dev
tools) and the `local-eval` test package.

Optionally install the pre-commit hooks:

```bash
make hooks
```

Note: don't use `uv run` to execute Python commands — it re-syncs the lockfile and
can overwrite editable installs. Use `python` directly instead.

### Dependencies and the cooldown

`uv.lock` pins every runtime and dev dependency. The build backends (`hatchling`,
`hatch-vcs`) are not in it; they resolve at build time, under the same cooldown.
CI installs from `uv.lock`, and fails when it is out of date with
`pyproject.toml`. When you change dependencies in `pyproject.toml`, run `uv lock`
and commit both files.

`pyproject.toml` sets `exclude-newer = "7 days"` under `[tool.uv]`, so `uv lock`,
`uv sync` and `uv pip` only pick releases that have been on PyPI for at least
seven days. A compromised release is usually found and removed within that time,
before it reaches `uv.lock`, CI or your machine. A few packages wait 6 hours
instead, so Flow can adopt a new release the day it ships: `inspect-ai`,
`inspect-scout`, and the `anthropic` and `openai` SDKs. They are listed with
`"6 hours"` in `[tool.uv.exclude-newer-package]`. Only a direct dependency (a
package in `dependencies` or the `dev` extra in `pyproject.toml`) that is a model
provider SDK or an Inspect package gets this exception. Every other package keeps
the seven-day cooldown, including the CA bundle (`certifi`). Dependabot's `uv`
entry in `.github/dependabot.yml` repeats the cooldown and the list, except
`inspect-ai`, which it ignores (`.github/workflows/inspect-update.yml` bumps it).
When you add a `"6 hours"` entry, also add the package to `cooldown.exclude` and
the `six-hour-cooldown` group there. `tests/test_dependency_cooldown.py` checks
that the two files match.

Dependabot proposes `uv.lock` updates daily, once a release has cleared its
cooldown. To adopt a release sooner, run `uv lock --upgrade-package <package>` and
commit `uv.lock`. A release still inside its cooldown can't be locked; wait for it
rather than overriding `exclude-newer`.

## Checks and tests

Run linting, formatting, and type checking (ruff + pyright):

```bash
make check
```

Run the test suite:

```bash
make test
```

To run a single test:

```bash
pytest tests/path/to/test_file.py::test_function_name -v
```

For a coverage report, use `make cov`.

## Commit messages and releases

We use [Conventional Commits](https://www.conventionalcommits.org/). Because we
squash-merge, **the PR title becomes the commit message** — so the title is what
matters. Format it as `<type>: <description>`.

Releases are automated with [Release Please](https://github.com/googleapis/release-please):
**don't edit `CHANGELOG.md` or bump the version by hand.** Release Please reads the
merged commit types, opens a release PR that updates the changelog and version, and
merging that PR tags the release; the publish then runs once a maintainer approves
the deployment.

Choose the type deliberately — `feat:` and `fix:` drive the version bump and
headline the release notes:

| Type | Effect |
| --- | --- |
| `feat:` | a user-facing feature — bumps the minor version |
| `fix:` | a user-facing bug fix — bumps the patch version |
| `feat!:` / `BREAKING CHANGE:` footer | bumps the minor version (pre-1.0 policy) and is called out in the release notes |
| `perf:`, `revert:` | appear in the release notes (no bump on their own) |
| `docs:`, `refactor:`, `chore:`, `build:`, `ci:`, `test:`, `style:` | hidden from the release notes |

Anything that isn't a user-facing feature or fix should avoid `feat:`/`fix:` so it
stays out of the headline sections.

## Reporting issues

Found a bug or have a feature request? Please open an issue on the
[GitHub issue tracker](https://github.com/meridianlabs-ai/inspect_flow/issues).
