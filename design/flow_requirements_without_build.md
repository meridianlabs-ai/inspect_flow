# Recording flow-requirements.txt without a build

## Overview

After it builds the evaluation environment, Flow records the installed packages in `flow-requirements.txt` in the log directory: `uv pip freeze` lists them, and `uv pip compile --no-deps --generate-hashes` adds the hash of each distribution. For a package installed from source (an editable checkout, a local directory, a VCS URL or a source archive URL), that compile builds the package's metadata, which downloads and runs its build backend without Flow's release cooldown.

This design stops the compile from fetching anything it would run. Flow splits the frozen list in two: registry pins (`name==version`) and wheel URLs go through the compile as today, which reads their hashes from the index or the wheel file without building; every other line is written to `flow-requirements.txt` exactly as `uv pip freeze` printed it. For editable, directory and VCS lines that is what the compile outputs anyway. A source archive line loses only the separate `--hash` option the compile adds; a digest the installer recorded stays in the URL's `#sha256=` fragment. The compile also runs with `--no-build-isolation`, so if a uv setting (an override or a constraint) still turns a pin into a source build, uv cannot resolve or download build requirements: it uses a backend already installed in the recorded environment, or the compile fails and Flow logs its usual warning. With no build requirement ever fetched, the compile needs no cooldown.

## Why

`write_flow_requirements` runs after every venv-mode install (and before every in-process `flow run` that is not a dry run). Its compile is given no Flow uv settings, so it has no release cooldown. For an editable package whose metadata is dynamic (an inspect_flow checkout with a `hatch-vcs` version, a user's eval project with a dynamic version, which `uv sync` installs editable), uv resolves the package's build requirements from the index and runs the backend in an isolated build environment. With a usable uv cache it reuses the build the install just made under the cooldown; with `UV_NO_CACHE=1`, or a cache cleared between the two commands, it resolves `hatchling`, `hatch-vcs` and their dependencies afresh, and can download and run a release younger than 7 days. That is exactly what the cooldown exists to prevent.

Giving the compile the cooldown is not straightforward, because the same compile must accept the installed runtime versions, which can be newer than the cooldown (versions copied from the host, versions fixed by a `uv.lock`). The three ways of reconciling the two (a package-wide exemption for installed versions, exact build constraints at those versions, forwarding the project's uv settings) each break something; see [Alternatives considered](#alternatives-considered).

## Goals and non-goals

Goals:

- The `flow-requirements.txt` step never resolves or downloads a build requirement, whatever the state of the uv cache and whatever uv settings reach it, in both venv and in-process mode (they share the function). For the lines Flow's installs produce, it builds nothing at all.
- `flow-requirements.txt` keeps its format and content: every installed package, with hashes for registry and wheel distributions.
- The installed runtime versions are recorded whatever their age.

Non-goals:

- No change to how the environment is installed or to the cooldown the install uses.
- No change to which uv settings the compile reads (still the caller's environment and user-level uv configuration, not the dependency project's settings in venv mode). The compile gains one command-line flag, `--no-build-isolation`, which takes precedence over any setting.
- No hashes for lines that have none today (editable, local directory, VCS).

## Current behaviour

`write_flow_requirements` (`src/inspect_flow/_launcher/freeze.py:14`):

1. runs `uv pip freeze --python <python>` (`freeze.py:24`) and deduplicates the lines by package name (`freeze.py:29`, `_deduplicate_freeze_requirements` at `freeze.py:72`);
2. writes the result to a temporary `.in` file in `cwd` and runs `uv pip compile --python <python> --generate-hashes --no-header --no-annotate --no-deps <file>` (`freeze.py:40-58`) with the caller's `env` and `cwd`;
3. writes the compile's stdout to `<log_dir>/flow-requirements.txt`; if the compile fails it logs a warning and writes no file (`freeze.py:62-67`).

Callers:

- Venv mode calls it at the end of `_create_venv` (`src/inspect_flow/_launcher/venv.py:254`) with `cwd` set to the temporary directory and the plain `env`. The install just before it (`venv.py:243-252`) uses `uv_pinned_settings`, which carries Flow's default cooldown; the compile does not. `test_cooldown_no_file` asserts this (`tests/test_venv.py:1566-1569`: the compile's env is the caller's, with no `--project`).
- In-process mode calls it from `inproc_launch` (`src/inspect_flow/_launcher/inproc.py:20`) with `cwd="."` and `os.environ`.

Both callers pass the caller's environment, so every uv setting the user has reaches the compile: `UV_*` variables, the user-level `uv.toml`, and in-process also the project's settings. The [uv settings documentation](../docs/advanced.qmd) (section "uv Settings and Release Cooldown") describes these for the install. Among them, an override (`UV_OVERRIDE`, `override-dependencies`) or a constraint (`UV_CONSTRAINT`, `constraint-dependencies`) that names a source for a package (`name @ file:///<dir>`) turns that package's registry pin into a source requirement in the compile, which then builds it like any other source line, resolving its build requirements from the index. `UV_OVERRIDE` and `UV_CONSTRAINT` apply only to `uv pip` commands, so a `uv sync` install can leave a registry version that the compile then rebuilds from the override.

What `uv pip freeze` prints, by how a package was installed, and what the compile does with each line (`UV_NO_CACHE=1`, read from uv's `-v` log):

| Installed from | Freeze line | Compile builds metadata? | Compile output |
|---|---|---|---|
| Index | `name==version` | No, even for a version with only an sdist (`docopt==0.6.2`): with `--no-deps` uv picks the file by name and reads no metadata | line plus `--hash` for every file of that version |
| Wheel URL (`https://` or `file://`) | `name @ <url>.whl` | No | line plus the wheel's `--hash` |
| Source archive URL | `name @ <url>.tar.gz`, ending in `#sha256=<digest>` when the installer recorded the archive's digest in `direct_url.json` (pip does; uv does not, even when the requirement carried a digest) | Yes (`setuptools.build_meta` for `docopt`) | line plus the archive's `--hash` |
| Local directory | `name @ file:///<dir>` | Yes when the metadata is dynamic (an inspect_flow checkout ran `hatchling` `prepare_metadata_for_build_wheel`); no when `[project]` is static (`tests/local_eval`) | line unchanged, no hash |
| VCS | `name @ git+<url>@<sha>` | Yes when dynamic (a clone of inspect_flow at a commit) | line unchanged, no hash |
| Editable | `-e file:///<dir>` | Yes when dynamic (the inspect_flow checkout: uv resolved `hatchling`, `hatch-vcs`, `setuptools-scm` and their dependencies and called `prepare_metadata_for_build_editable`) | line unchanged, no hash |

Over a freeze of all six kinds, the compile's output repeats every input line unchanged apart from the added hashes; uv lists editable lines first and the rest by name. The compile also echoes a URL's credentials unchanged; uv strips them from `direct_url.json` at install, so a freeze of a uv-built environment has none.

With `--no-build-isolation`, uv neither resolves nor installs build requirements: a source build runs the backend from the `--python` environment, and fails ("No module named 'hatchling'") when it is not installed there. Registry pins, including sdist-only ones, and wheel URLs compile as before with the flag.

Where each shape comes from in Flow:

- Registry pins: everything resolved from an index by `uv sync`, `uv pip install -r` or the final install, including packages copied from the host at their installed version (`_get_pip_string_with_version`, `src/inspect_flow/_launcher/pip_string.py:27`).
- Editable: the dependency project itself (`uv sync` installs it editable), editable path dependencies in a dependency file, and a host `inspect-flow` or `inspect-ai` installed editable (`pip_string.py:107-112`, and `pip_string.py:20-24` for a Flow checkout).
- Local directory and VCS: `additional_dependencies` (the docs list PyPI packages, Git repositories and local packages, `docs/advanced.qmd:116`; paths are made absolute by `_resolve_dependency`, `venv.py:257`) and host packages installed that way (`pip_string.py:93-116`).
- Archive URLs: a URL in `additional_dependencies` or a dependency file, or a host package installed from one (`pip_string.py:118-130`; Flow passes the host's recorded digest as a `#sha256=` fragment, which uv then does not record). No example, doc or satellite checkout (`hawk`, `inspect-action`, `inspect_swarm`, `flow_steps_demo`, `actions`) uses one.

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
    if requirement.url is None:
        return True
    return urlparse(requirement.url).path.endswith(".whl")
```

`Requirement` is `packaging.requirements.Requirement` (already used by `uv_settings.py` and `venv.py`), `urlparse` is from `urllib.parse`. The suffix is checked on the URL's path, which excludes a `#sha256=` fragment and any query. A wheel URL whose `.whl` suffix is percent-encoded is not recognized and is recorded as written, without a hash; nothing produces one, and the fallback builds and fetches nothing. A line `packaging` cannot parse is an editable line or something uv printed that Flow does not recognize; either way it is recorded as written, which is what the compile does today for the shapes it does not hash.

In `write_flow_requirements`:

```python
lines = _deduplicate_freeze_requirements(freeze_result.stdout).splitlines()
as_written = [line for line in lines if not _compiles_without_build(line)]
to_compile = [line for line in lines if _compiles_without_build(line)]
# the temporary .in file now holds "".join(f"{line}\n" for line in to_compile)
# the compile command gains "--no-build-isolation"; error handling as today
f.write("".join(f"{line}\n" for line in as_written) + compile_result.stdout)
```

- **No build requirement is fetched.** The split keeps every source line Flow's installs produce out of the compile. `--no-build-isolation` covers what the split cannot see: a uv setting that rewrites a pin into a source (an override or constraint, from the environment, the user's `uv.toml`, or in-process the project's settings), or a uv release that builds registry sdists for metadata under `--no-deps`. In each case uv runs only a backend already installed in the recorded environment, which the install put there under its cooldown, or the build fails, the compile fails and Flow logs its existing warning and writes no file. Flow does not strip or override those settings: they keep applying to the compile as they do today, and only build isolation is turned off. The flag is a command-line option, which takes precedence over any `no-build-isolation` setting.
- **No cooldown.** The compile resolves only the pins and wheels it is given and never a build requirement, so there is nothing for a cooldown to hold back, and a cooldown would reject an installed runtime version newer than the cutoff.
- The compile's `env`, `cwd` and other flags are unchanged.
- The compile always runs, even when every line is recorded as written: uv accepts an empty requirements file (it warns and exits 0), and one code path is shorter than a special case.
- Output order: the as-written lines first, in freeze order (sorted by name), then the compile's output (sorted by name). Today editable lines come first and the rest are sorted together; the new order differs only in where non-editable source lines fall.
- Error handling is unchanged: a failed freeze raises as today; a failed compile logs the same warning and writes no file. A source line whose metadata build fails no longer fails the compile, so the file is now written in that case.
- Concurrency is unchanged: the temporary input file is still unique per call (`test_712_concurrent_flow_requirements_no_race`).

Documentation: the paragraph in `docs/advanced.qmd` that says the default cooldown does not apply to this step and that it can fetch a newer build requirement (`docs/advanced.qmd:143`) is replaced by: recording `flow-requirements.txt` never downloads a build requirement. Editable, local directory, VCS and source archive packages are recorded as `uv pip freeze` lists them, without a `--hash` option; a source archive URL keeps a `#sha256=` digest when its installer recorded one, which uv does not.

## Alternatives considered

**Give the compile Flow's cooldown, exempt the installed versions, and constrain builds to them.** The exemption in uv (`exclude-newer-package = false`) is per package, so it also lets a build pick a newer version of any installed package; exact build constraints make the compile unsatisfiable when a backend needs another version of an installed package, or when the user's own build constraints pin a different one. The problems are inherent to running one resolution for both runtime pins and build requirements.

**Forward the project's uv settings (`--project`) with Flow's default cooldown and no constraints, and fix the output with `--output-file` and `--format requirements.txt`.** The cooldown would then match the install's for build requirements. But the compile would still build every dynamic source package, for output identical to its input, and every other `[tool.uv.pip]` setting would also reach it (`universal`, `emit-index-url`, `no-build`, `python-platform`, ...), each changing or breaking the recorded file. Pinning each of those on the command line is a list that grows with uv.

**Two compiles: registry pins and wheels as today, source lines with Flow's default cooldown (`uv_settings_env` without pins).** The source lines are URLs, which the cooldown does not restrict, so only their build requirements would be held back; a source archive would keep its `--hash`. It still builds editable, directory and VCS packages for no change in output, doubles the uv calls, and fails the record where the install succeeded whenever the project's own settings allow a newer build requirement than Flow's default. The one gain, a `--hash` for source archive URLs, is for a shape nothing in use produces.

**Isolate the compile from the user's settings (`--no-config` and removing `UV_OVERRIDE`, `UV_CONSTRAINT` from its environment) instead of `--no-build-isolation`.** It would stop overrides and constraints from reaching the compile, but `--no-config` also drops the index, find-links and authentication settings of the user's `uv.toml`, which the compile needs to find the pinned versions' hashes on a private index, and the list of environment variables to remove grows with uv. It also leaves a uv that builds registry sdists free to fetch build requirements. `--no-build-isolation` closes every route with one flag and leaves index settings alone.

**Rely on the uv cache to reuse the install's build.** This is today's behaviour; it fails exactly in the cases the issue describes (`UV_NO_CACHE`, a cleared cache), and uv has no other way to hand one command's built metadata to another.

**`uv pip compile --no-build`.** It refuses every dynamic source package and also every registry version that has only an sdist (`docopt==0.6.2`: "has no usable wheels"), so the record would fail outright in those environments.

**Hash source archives in Flow (download and `sha256`).** It restores the archive `--hash`, but reimplements what uv does, adds network code to Flow, and serves a shape nothing in use produces.

## Compatibility and migration

- `flow-requirements.txt` stays a requirements file with the same lines. Differences: non-editable source lines (directory, VCS, source archive) now come before the registry pins instead of among them; the file is written when a source package's metadata build would have failed; and a source archive URL line no longer has the `--hash` option the compile added.
- A source archive line keeps the digest its installer recorded, as a `#sha256=` fragment in the URL. uv records none, so in venv mode, and in-process for archives uv installed, the line has no digest: the hash the compile computed is lost. This cost is accepted, since nothing in use installs from a source archive (decision: Ransom, 2026-11-12). For a pip-installed archive, in-process, the fragment carries the same digest the `--hash` option did.
- `--require-hashes`: a file with editable, directory or VCS lines could never be installed with it. A source archive line with a `#sha256=` fragment installs with `uv pip install --require-hashes` alongside `--hash` pins; whether pip accepts the fragment in place of `--hash` is not confirmed here. A line without a digest is rejected, so a file whose only unhashed lines were source archives installed by uv could be installed that way until now and no longer can.
- An override or constraint that rewrites a pin into a source whose backend is not installed in the environment now fails the record (warning, no file) where today it downloads the backend and succeeds.
- No public API, CLI option, spec field, schema or generated type changes. Nothing in Flow reads `flow-requirements.txt` back (the only references are the writer, its tests and the docs).

## Security

- The input is `uv pip freeze` output for the environment Flow just built (or, in-process, the running one): package names and URLs from installed metadata, which came from the user's dependencies. It is parsed with `packaging` and written to a temporary file and the log directory; it never reaches a shell or a command line.
- The change removes the route by which a release younger than the cooldown could run: the compile never resolves or downloads a build requirement. A build it still performs (forced by an override or constraint) runs only a backend already installed in the environment it records, which the evaluation itself runs code from.
- User uv settings still reach the compile as today; the only setting Flow fixes, build isolation, is one that removes network fetches.
- Lines written as is contain exactly what the compile would have written for them, minus the archive `--hash`: the compile echoes URLs unchanged, credentials included, and uv strips credentials from the URL it records at install.

## Testing

All in `tests/test_venv.py`, offline, using the existing local index helper `_simple_index` (`tests/test_venv.py:1595`), extended to list `*.tar.gz` as well as `*.whl` and to record the project names it is asked for.

- **New: `test_flow_requirements_builds_nothing`.** Build a fixture: a source package directory whose `pyproject.toml` declares `dynamic = ["version"]` and `requires = ["missing-backend"]` (a backend neither the local index nor the environment has); a wheel `copied-dep 2.0` and an sdist `sdist-only 1.0`, whose own build also requires `missing-backend`, on the local index; and a local source archive. Stub only `uv pip freeze` to print `-e file://<pkg>`, `other-pkg @ file://<pkg>`, `vcs-pkg @ git+file:///<missing repo>@<sha>`, `src-archive @ file://<archive>.tar.gz#sha256=<digest>`, `copied-dep==2.0`, `sdist-only==1.0` and `wheel-pkg @ file://<wheel>` (a local wheel made with the existing `_wheel` helper), and run the real compile with `UV_INDEX_URL` set to the index and `UV_NO_CACHE=1`. Assert the file holds the four source lines exactly, the archive line with its `#sha256=` fragment preserved and no `--hash` option under it; hashes for `copied-dep`, `sdist-only` and `wheel-pkg`; that the index was never asked for `missing-backend`; and that no warning was logged. Today the compile tries to resolve `missing-backend` (and to clone the missing repository), fails, and writes no file, so the test reproduces the issue. The `sdist-only` pin guards the assumption that uv does not build a registry sdist under `--no-deps`.
- **New: `test_flow_requirements_settings_cannot_fetch_build_requirements`.** Set `UV_OVERRIDE` to a file rewriting `copied-dep` to `copied-dep @ file://<pkg>` (the dynamic package above). One route suffices: the flag does not depend on how the source requirement reached the compile, and the other routes (constraints, `uv.toml`) differ only in how uv reads its settings. Freeze prints only `copied-dep==2.0`. Assert the index was never asked for `missing-backend` and that the warning was logged with no file written. Without `--no-build-isolation` the compile asks the index for `missing-backend`, so the test fails.
- **Updated: `test_5_flow_requirements`** (`tests/test_venv.py:702`). Its stub prints `mocked output` for both the freeze and the compile; that line is not a requirement, so it would now appear twice. Give the freeze and the compile distinct stdout values, the freeze's a registry pin, and assert the file equals the compile's stdout (with only registry pins, nothing is recorded as written).
- **Updated: `test_freeze_forwards_explicit_interpreter_to_uv`**: also assert the compile command carries `--no-build-isolation`.
- **Unchanged and still guarding:** `test_cooldown_no_file` (the compile gets the caller's env and no `--project`), `test_712_concurrent_flow_requirements_no_race` and `test_freeze_targets_explicit_interpreter_not_virtual_env`, whose freeze lines are registry pins and still reach the compile.
- The slow dependency-file tests (`test_241_*`) keep asserting that `local_eval` appears; it is now an as-written editable line. CI runs `--runslow`.

## Implementation plan

One PR (`fix:`, since it stops an unvetted build backend from running):

1. `src/inspect_flow/_launcher/freeze.py`: add `_compiles_without_build`, split the deduplicated lines, compile only the ones it accepts with `--no-build-isolation` added, write the others first.
2. `tests/test_venv.py`: extend `_simple_index` to serve sdists and record requested names; add the two new tests; update `test_5_flow_requirements` and `test_freeze_forwards_explicit_interpreter_to_uv`.
3. `docs/advanced.qmd`: replace the `flow-requirements.txt` cooldown paragraph as described under Design.

## Open questions

None.

## Not this design

- In in-process mode the compile runs in the user's working directory, so uv reads that project's `[tool.uv.pip]` settings; with `output-file` set, the internal compile overwrites the user's exported requirements file. Passing an explicit `--output-file` to a temporary path, or running the compile in a temporary directory, would fix it.
- An override or constraint that changes a pinned version (rather than its source) makes the compile record the overridden version instead of the installed one.
- When the compile fails (an index that does not serve a pinned version, an offline run), no `flow-requirements.txt` is written at all; the frozen lines without hashes would still be a useful record.
