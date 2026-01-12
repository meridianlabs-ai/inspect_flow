# Changelog

## [0.1.4](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.1.3...v0.1.4) (2026-01-12)


### Bug Fixes

* correctly write flow-requirements.txt to s3 ([#375](https://github.com/meridianlabs-ai/inspect_flow/issues/375)) ([abaecd4](https://github.com/meridianlabs-ai/inspect_flow/commit/abaecd493a962717e7177a9462d6b9a434df429c))

## [0.1.3](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.1.2...v0.1.3) (2026-01-06)


### Bug Fixes

* ensure logging works in run process in venv ([#343](https://github.com/meridianlabs-ai/inspect_flow/issues/343)) ([530eb8e](https://github.com/meridianlabs-ai/inspect_flow/commit/530eb8e5902ef3212bd12f63e22980a34e812b8e))
* improved errors on duplicate tasks ([#353](https://github.com/meridianlabs-ai/inspect_flow/issues/353)) ([21fd03c](https://github.com/meridianlabs-ai/inspect_flow/commit/21fd03cf58432b793bffbe627a1e688143decad2))
* remove unneeded generated types (and package upgrade) ([#349](https://github.com/meridianlabs-ai/inspect_flow/issues/349)) ([844ab79](https://github.com/meridianlabs-ai/inspect_flow/commit/844ab79812ecd9b324c2c213c5ca50b9318823a6))
* support s3 paths on CLI ([#339](https://github.com/meridianlabs-ai/inspect_flow/issues/339)) ([b63f483](https://github.com/meridianlabs-ai/inspect_flow/commit/b63f4839593ebeb821b0b14d451a8864365c5ab3))
* use python version specified in uv.lock file ([#352](https://github.com/meridianlabs-ai/inspect_flow/issues/352)) ([291a89b](https://github.com/meridianlabs-ai/inspect_flow/commit/291a89b5c0ed446bd3f142d18924a2f149090cdb))

## [0.1.2](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.1.1...v0.1.2) (2025-12-15)


### Bug Fixes

* add logging of include files ([#330](https://github.com/meridianlabs-ai/inspect_flow/issues/330)) ([29f6c8c](https://github.com/meridianlabs-ai/inspect_flow/commit/29f6c8c6e443a158069471573643f209b7db26b6))
* add uv_sync_args to dependency configuration ([#328](https://github.com/meridianlabs-ai/inspect_flow/issues/328)) ([89dfd51](https://github.com/meridianlabs-ai/inspect_flow/commit/89dfd51118f84b0eb46249701e4f709aa0c8dfe6))
* Do not write flow-requirements.txt if dry_run ([#335](https://github.com/meridianlabs-ai/inspect_flow/issues/335)) ([fd1d42a](https://github.com/meridianlabs-ai/inspect_flow/commit/fd1d42a16a482e90089d0af45a2dca6868dc98de))
* maintain package version for installed packages in venv ([#332](https://github.com/meridianlabs-ai/inspect_flow/issues/332)) ([a7564db](https://github.com/meridianlabs-ai/inspect_flow/commit/a7564db0f93ded2dcee86083601c2bc62521e05a))
* warning when multiple dependency files found ([#337](https://github.com/meridianlabs-ai/inspect_flow/issues/337)) ([3fa1239](https://github.com/meridianlabs-ai/inspect_flow/commit/3fa123944bcaf225eafaed7e74f63ad637e989a8))

## [0.1.1](https://github.com/meridianlabs-ai/inspect_flow/compare/0.1.0...v0.1.1) (2025-12-11)


### Bug Fixes

* Rename FlowJob to FlowSpec
* Fix log paths in Inspect output
* Rename bundle_url_map to bundle_url_mappings
* Apply defaults when loading FlowSpec


### Documentation

* Add CHANGELOG.md ([#322](https://github.com/meridianlabs-ai/inspect_flow/issues/322)) ([0f5a294](https://github.com/meridianlabs-ai/inspect_flow/commit/0f5a29464b144ca34927eb393d03e56e8ccd780b))

## [0.1.0](https://github.com/meridianlabs-ai/inspect_flow/releases/tag/0.1.0) (2025-12-05)

### Features
* Flow support for configuration repeatability and sharing
