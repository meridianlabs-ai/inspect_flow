# Contributing to Inspect Flow

Thanks for contributing to Inspect Flow! This guide covers local setup, the checks
we run, and how commits and releases work.

## Development setup

Inspect Flow requires Python 3.10 or later. Clone the repository and sync the
environment (this installs the `dev` dependency group by default):

```bash
git clone https://github.com/meridianlabs-ai/inspect_flow
cd inspect_flow
uv sync
source .venv/bin/activate
```

Optionally install the pre-commit hooks:

```bash
make hooks
```

Note: don't use `uv run` to execute Python commands — it re-syncs the lockfile and
can overwrite editable installs. Use `python` directly instead.

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
merging that PR tags and publishes the release.

Choose the type deliberately — only `feat:` and `fix:` appear in the release notes
and drive the version bump:

| Type | Use for |
| --- | --- |
| `feat:` | a user-facing feature |
| `fix:` | a user-facing bug fix |
| `docs:`, `refactor:`, `perf:`, `test:`, `build:`, `chore:`, `ci:` | everything else — excluded from the release notes |

Anything that isn't a user-facing feature or fix should avoid `feat:`/`fix:` so it
stays out of the release notes.

## Reporting issues

Found a bug or have a feature request? Please open an issue on the
[GitHub issue tracker](https://github.com/meridianlabs-ai/inspect_flow/issues).
