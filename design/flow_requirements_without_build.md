# Recording flow-requirements.txt without a build

## Overview

After it builds the evaluation environment, Flow records the installed packages in `flow-requirements.txt` in the log directory: `uv pip freeze` lists them, and `uv pip compile --no-deps --generate-hashes` adds the hash of each distribution. For a package installed from source (an editable checkout, a local directory, a VCS URL or a source archive URL), that compile builds the package's metadata, which downloads and runs its build backend without Flow's release cooldown.

This design stops the compile from building anything. Flow splits the frozen list in two: registry pins (`name==version`) and wheel URLs go through the compile as today, which reads their hashes from the index or the wheel file without running any package code; every other line is written to `flow-requirements.txt` exactly as `uv pip freeze` printed it. Those are the lines for which the compile adds no hash and echoes the input unchanged anyway, so the file keeps the same content, except that a source archive URL is no longer hashed. No cooldown is needed for the compile, because it no longer fetches anything it would run.

## Why

`write_flow_requirements` runs after every venv-mode install (and before every in-process `flow run` that is not a dry run). Its compile is given no Flow uv settings, so it has no release cooldown. For an editable package whose metadata is dynamic (an inspect_flow checkout with a `hatch-vcs` version, a user's eval project with a dynamic version, which `uv sync` installs editable), uv resolves the package's build requirements from the index and runs the backend in an isolated build environment. With a usable uv cache it reuses the build the install just made under the cooldown; with `UV_NO_CACHE=1`, or a cache cleared between the two commands, it resolves `hatchling`, `hatch-vcs` and their dependencies afresh, and can download and run a release younger than 7 days. That is exactly what the cooldown exists to prevent.

Giving the compile the cooldown is not straightforward, because the same compile must accept the installed runtime versions, which can be newer than the cooldown (versions copied from the host, versions fixed by a `uv.lock`). The three ways of reconciling the two (a package-wide exemption for installed versions, exact build constraints at those versions, forwarding the project's uv settings) each break something; see [Alternatives considered](#alternatives-considered).

## Goals and non-goals

Goals:

- The `flow-requirements.txt` step downloads and runs no build backend, whatever the state of the uv cache, in both venv and in-process mode (they share the function).
- `flow-requirements.txt` keeps its format and content: every installed package, with hashes for registry and wheel distributions.
- The installed runtime versions are recorded whatever their age.

Non-goals:

- No change to how the environment is installed or to the cooldown the install uses.
- No change to which uv settings the compile reads (still the caller's environment and user-level uv configuration, not the dependency project's settings in venv mode).
- No hashes for lines that have none today (editable, local directory, VCS).

## Current behaviour

uv behaviour below was checked with uv 0.13.7.

`write_flow_requirements` (`src/inspect_flow/_launcher/freeze.py:14`):

1. runs `uv pip freeze --python <python>` (`freeze.py:24`) and deduplicates the lines by package name (`freeze.py:29`, `_deduplicate_freeze_requirements` at `freeze.py:72`);
2. writes the result to a temporary `.in` file in `cwd` and runs `uv pip compile --python <python> --generate-hashes --no-header --no-annotate --no-deps <file>` (`freeze.py:40-58`) with the caller's `env` and `cwd`;
3. writes the compile's stdout to `<log_dir>/flow-requirements.txt`; if the compile fails it logs a warning and writes no file (`freeze.py:62-67`).

Callers:

- Venv mode calls it at the end of `_create_venv` (`src/inspect_flow/_launcher/venv.py:254`) with `cwd` set to the temporary directory and the plain `env`. The install just before it (`venv.py:243-252`) uses `uv_pinned_settings`, which carries Flow's default cooldown; the compile does not. `test_cooldown_no_file` asserts this (`tests/test_venv.py:1566-1569`: the compile's env is the caller's, with no `--project`).
- In-process mode calls it from `inproc_launch` (`src/inspect_flow/_launcher/inproc.py:20`) with `cwd="."` and `os.environ`.

What `uv pip freeze` prints, by how a package was installed, and what the compile does with each line (each checked by running `uv pip install`, `uv pip freeze` and the exact compile command in a scratch environment, with `UV_NO_CACHE=1` and `-v` to see builds):

| Installed from | Freeze line | Compile builds metadata? | Compile output |
|---|---|---|---|
| Index | `name==version` | No, even for a version with only an sdist (`docopt==0.6.2`): with `--no-deps` uv picks the file by name and reads no metadata | line plus `--hash` for every file of that version |
| Wheel URL (`https://` or `file://`) | `name @ <url>.whl` | No | line plus the wheel's `--hash` |
| Source archive URL | `name @ <url>.tar.gz` | Yes (`setuptools.build_meta` for `docopt`) | line plus the archive's `--hash` |
| Local directory | `name @ file:///<dir>` | Yes when the metadata is dynamic (an inspect_flow checkout ran `hatchling` `prepare_metadata_for_build_wheel`); no when `[project]` is static (`tests/local_eval`) | line unchanged, no hash |
| VCS | `name @ git+<url>@<sha>` | Yes when dynamic (a clone of inspect_flow at a commit) | line unchanged, no hash |
| Editable | `-e file:///<dir>` | Yes when dynamic (the inspect_flow checkout: uv resolved `hatchling`, `hatch-vcs`, `setuptools-scm` and their dependencies and called `prepare_metadata_for_build_editable`) | line unchanged, no hash |

Comparing the compile's output with its input over a freeze of all six kinds showed every line unchanged apart from the added hashes; uv lists editable lines first and the rest by name. The compile also echoes a URL's credentials unchanged; uv strips them from `direct_url.json` at install, so a freeze of a uv-built environment has none.

Where each shape comes from in Flow:

- Registry pins: everything resolved from an index by `uv sync`, `uv pip install -r` or the final install, including packages copied from the host at their installed version (`_get_pip_string_with_version`, `src/inspect_flow/_launcher/pip_string.py:27`).
- Editable: the dependency project itself (`uv sync` installs it editable), editable path dependencies in a dependency file, and a host `inspect-flow` or `inspect-ai` installed editable (`pip_string.py:107-112`, and `pip_string.py:20-24` for a Flow checkout).
- Local directory and VCS: `additional_dependencies` (the docs list PyPI packages, Git repositories and local packages, `docs/advanced.qmd:116`; paths are made absolute by `_resolve_dependency`, `venv.py:257`) and host packages installed that way (`pip_string.py:93-116`).
- Archive URLs: a URL in `additional_dependencies` or a dependency file, or a host package installed from one (`pip_string.py:118-130`). No example, doc or satellite checkout (`hawk`, `inspect-action`, `inspect_swarm`, `flow_steps_demo`, `actions`) uses one.

## Design

`write_flow_requirements` keeps its signature, its callers, the freeze and the deduplication. Between deduplication and compile it splits the lines:

```python
def _compiles_without_build(line: str) -> bool:
    # uv reads a registry pin's or a wheel's name and version without building;
    # any other source is built for its metadata, and the compile adds no hash.
    try:
        requirement = Requirement(line)
    except InvalidRequirement:
        return False  # `-e <url>`
    return requirement.url is None or urlparse(requirement.url).path.endswith(".whl")
```

`Requirement` is `packaging.requirements.Requirement` (already used by `uv_settings.py` and `venv.py`), `urlparse` is `urllib.parse.urlparse`. A line `packaging` cannot parse is an editable line or something uv printed that Flow does not recognize; either way it is recorded as written, which is what the compile does today for the shapes it does not hash.

In `write_flow_requirements`:

```python
lines = _deduplicate_freeze_requirements(freeze_result.stdout).splitlines()
as_written = [line for line in lines if not _compiles_without_build(line)]
to_compile = [line for line in lines if _compiles_without_build(line)]
# the temporary .in file now holds "".join(f"{line}\n" for line in to_compile)
# ... the same compile command and error handling as today ...
f.write("".join(f"{line}\n" for line in as_written) + compile_result.stdout)
```

- The compile command, its `env`, `cwd` and flags are unchanged. It gets no cooldown: it now resolves only the pins and wheels it is given, never a build requirement, so there is nothing for a cooldown to hold back, and a cooldown would reject an installed runtime version newer than the cutoff.
- The compile always runs, even when every line is recorded as written: uv accepts an empty requirements file (it warns and exits 0; verified), and one code path is shorter than a special case.
- Output order: the as-written lines first, in freeze order (sorted by name), then the compile's output (sorted by name). Today editable lines come first and the rest are sorted together; the new order differs only in where non-editable source lines fall.
- Error handling is unchanged: a failed freeze raises as today; a failed compile logs the same warning and writes no file. A source package whose metadata build fails no longer fails the compile, so the file is now written in that case.
- Concurrency is unchanged: the temporary input file is still unique per call (`test_712_concurrent_flow_requirements_no_race`).

Documentation: the paragraph in `docs/advanced.qmd` that says the default cooldown does not apply to this step and that it can fetch a newer build requirement (`docs/advanced.qmd:143`) is replaced by one sentence: recording `flow-requirements.txt` builds nothing; editable, local directory, VCS and source archive packages are recorded as `uv pip freeze` lists them, without hashes.

## Alternatives considered

**Give the compile Flow's cooldown, exempt the installed versions, and constrain builds to them.** The exemption in uv (`exclude-newer-package = false`) is per package, so it also lets a build pick a newer version of any installed package; exact build constraints make the compile unsatisfiable when a backend needs another version of an installed package, or when the user's own build constraints pin a different one. The problems are inherent to running one resolution for both runtime pins and build requirements.

**Forward the project's uv settings (`--project`) with Flow's default cooldown and no constraints, and fix the output with `--output-file` and `--format requirements.txt`.** The cooldown would then match the install's for build requirements. But the compile would still build every dynamic source package, for output identical to its input, and every other `[tool.uv.pip]` setting would also reach it (`universal`, `emit-index-url`, `no-build`, `python-platform`, ...), each changing or breaking the recorded file. Pinning each of those on the command line is a list that grows with uv.

**Two compiles: registry pins and wheels as today, source lines with Flow's default cooldown (`uv_settings_env` without pins).** The source lines are URLs, which the cooldown does not restrict, so only their build requirements would be held back; a source archive would keep its hash. It still builds editable, directory and VCS packages for no change in output, doubles the uv calls, and fails the record where the install succeeded whenever the project's own settings allow a newer build requirement than Flow's default. The one gain, a hash for source archive URLs, is for a shape nothing in use produces.

**Rely on the uv cache to reuse the install's build.** This is today's behaviour; it fails exactly in the cases the issue describes (`UV_NO_CACHE`, a cleared cache), and uv has no other way to hand one command's built metadata to another.

**`uv pip compile --no-build`.** It refuses every dynamic source package and also every registry version that has only an sdist (`docopt==0.6.2`: "has no usable wheels"; verified), so the record would fail outright in those environments.

**Hash source archives in Flow (download and `sha256`).** It restores the one lost hash, but reimplements what uv does, adds network code to Flow, and serves a shape nothing in use produces.

## Compatibility and migration

- `flow-requirements.txt` stays a requirements file with the same lines. Differences: non-editable source lines (directory, VCS, source archive) now come before the registry pins instead of among them; a source archive URL line no longer carries `--hash` (see [Open questions](#open-questions)); and the file is written when a source package's metadata build would have failed.
- A file with editable, directory or VCS lines could never be installed with `--require-hashes`; one whose only unhashed lines are source archive URLs could until now and no longer can.
- No public API, CLI option, spec field, schema or generated type changes. Nothing in Flow reads `flow-requirements.txt` back (the only references are the writer, its tests and the docs).

## Security

- The input is `uv pip freeze` output for the environment Flow just built (or, in-process, the running one): package names and URLs from installed metadata, which came from the user's dependencies. It is parsed with `packaging` and written to a temporary file and the log directory; it never reaches a shell or a command line.
- The change removes code execution: the compile no longer downloads and runs build backends for source packages, which is the path by which a release younger than the cooldown could run.
- Lines written as is contain exactly what the compile would have written for them: verified that the compile echoes URLs unchanged, credentials included, and that uv strips credentials from the URL it records at install.

## Testing

All in `tests/test_venv.py`, offline, using the existing local index helper `_simple_index` (`tests/test_venv.py:1595`).

- **New: `test_flow_requirements_builds_nothing`.** Build a fixture: a source package directory whose `pyproject.toml` declares `dynamic = ["version"]` and `requires = ["missing-backend"]` (a backend the local index does not have); a wheel `copied-dep 2.0` and an sdist `sdist-only 1.0`, whose own build also requires `missing-backend`, on the local index (extend `_simple_index` to list `*.tar.gz` as well as `*.whl`). Stub only `uv pip freeze` to print `-e file://<pkg>`, `other-pkg @ file://<pkg>`, `vcs-pkg @ git+file:///<missing repo>@<sha>`, `copied-dep==2.0`, `sdist-only==1.0` and `wheel-pkg @ file://<wheel>` (a local wheel made with the existing `_wheel` helper), and run the real compile with `UV_INDEX_URL` set to the index and `UV_NO_CACHE=1`. Assert the file holds the three source lines exactly, hashes for `copied-dep`, `sdist-only` and `wheel-pkg`, and that no warning was logged. Today the compile tries to resolve `missing-backend` (and to clone the missing repository), fails, and writes no file, so the test reproduces the issue. The `sdist-only` pin guards the design's central assumption: uv does not build a registry sdist under `--no-deps`.
- **Updated: `test_5_flow_requirements`** (`tests/test_venv.py:702`). Its stub prints `mocked output` for both the freeze and the compile; that line is not a requirement, so it would now appear twice. Make the freeze stub print a registry pin and assert the compile's output follows it.
- **Unchanged and still guarding:** `test_cooldown_no_file` (the compile gets the caller's env and no `--project`), `test_712_concurrent_flow_requirements_no_race`, `test_freeze_forwards_explicit_interpreter_to_uv` and `test_freeze_targets_explicit_interpreter_not_virtual_env`, whose freeze lines are registry pins and still reach the compile.
- The slow dependency-file tests (`test_241_*`) keep asserting that `local_eval` appears; it is now an as-written editable line. CI runs `--runslow`.

## Implementation plan

One PR (`fix:`, since it stops an unvetted build backend from running):

1. `src/inspect_flow/_launcher/freeze.py`: add `_compiles_without_build`, split the deduplicated lines, compile only the ones it accepts, write the others first.
2. `tests/test_venv.py`: extend `_simple_index` to serve sdists, add `test_flow_requirements_builds_nothing`, update `test_5_flow_requirements`.
3. `docs/advanced.qmd`: replace the `flow-requirements.txt` cooldown paragraph as described under Design.

## Open questions

- **Source archive URL lines lose their hash.** Recording them as written is what keeps the compile from building them; keeping the hash needs either a second, cooldown-limited compile or Flow hashing the archive itself (both under Alternatives). No current use installs from a source archive URL. Recommendation: accept the loss. Confidence: high.

## Not this design

- In in-process mode the compile runs in the user's working directory, so uv reads that project's `[tool.uv.pip]` settings; with `output-file` set, the internal compile overwrites the user's exported requirements file (verified with uv 0.13.7: a `[tool.uv.pip] output-file = "export.txt"` project gets `export.txt` written). Passing an explicit `--output-file` to a temporary path, or running the compile in a temporary directory, would fix it.
- When the compile fails (an index that does not serve a pinned version, an offline run), no `flow-requirements.txt` is written at all; the frozen lines without hashes would still be a useful record.
