# Security Policy

## Reporting a vulnerability

[Report a vulnerability](https://github.com/meridianlabs-ai/inspect_flow/security/advisories/new) through GitHub's private vulnerability reporting on this repository. Only you, the maintainers at Meridian Research Labs, and anyone they add to the report can see it. Please do not open a public issue, discussion, or pull request for a suspected vulnerability.

Include as much of the following as you can:

- The version of `inspect_flow` and `inspect_ai` you tested, your Python version and operating system
- A description of the problem and what an attacker could do with it
- Steps to reproduce it, ideally a small script or example
- Any logs, stack traces, or output that help show the behavior

## What to expect

- We will acknowledge your report within 3 business days.
- We will tell you within 10 business days whether we consider it a vulnerability and what we plan to do.
- We aim to release a fix within 30 days of the report. If a fix will take longer, we will tell you why.

We reply in the advisory and keep you updated there as we work on a fix.

We do not run a bug bounty program and cannot pay for reports.

## Supported versions

We only fix security issues in the most recent release of `inspect_flow` on PyPI. We do not backport fixes to older versions. If you are running an older version, upgrade before reporting.

## Scope

Flow specs, the files they include, and `_flow.py` files are code that you run. `flow run`, `flow check` and `flow config` run the spec, its includes, and any `_flow.py` in the spec's directory and the directories above it. A command that takes an `@NAME` argument or a `--filter` can run every `_flow.py` from the current directory up. A run with `execution_type="venv"` also installs the spec's dependencies, a `pyproject.toml` or `requirements.txt` it finds above the spec, and packages it infers from model and task names. The sections below describe what we treat as a vulnerability and what we do not.

### In scope

- Code execution or file access triggered by the contents of eval logs, a log store, or a log directory's `flow.yaml` that someone else wrote
- A flow loading or installing code from somewhere other than the places described above
- API keys, tokens, or other secrets written to eval logs, the log store, or error messages
- Flaws in our release process, packaging, or CI that would let someone publish or modify a release

### Out of scope

- Running `flow` in or below a directory that holds an untrusted spec or `_flow.py` runs that code, and a venv run installs what it finds there. Treat those files the same way you would treat any other Python you did not write.
- Vulnerabilities in `inspect_ai` should be reported under [its security policy](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/SECURITY.md).
- Vulnerabilities in other third-party dependencies should be reported to that project. Tell us if Inspect Flow needs a change in response, such as a version pin.
- Reports produced by a security scanner, or written mainly by an automated tool or a language model, with no working proof of concept. We will close these without a detailed response.

## Disclosure

When the fix is released, we publish the advisory from your report and request a CVE through GitHub where one applies. We will tell you before we publish it. The advisory credits you unless you ask us not to.

Please keep the details private until the advisory is published.
