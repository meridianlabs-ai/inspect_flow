# Changelog

## [0.1.5](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.1.4...v0.1.5) (2026-01-16)


### Bug Fixes

* add --log-dir-allow-dirty flag ([#416](https://github.com/meridianlabs-ai/inspect_flow/issues/416)) ([a27f79d](https://github.com/meridianlabs-ai/inspect_flow/commit/a27f79d936b62996a8936890104d3e93306e5815))
* Allow including flow spec objects ([#420](https://github.com/meridianlabs-ai/inspect_flow/issues/420)) ([52dade6](https://github.com/meridianlabs-ai/inspect_flow/commit/52dade680a09d2df7f3b8905770e3b21aa9bcbe2))
* auto collect dependencies from INSPECT_EVAL_MODEL ([#415](https://github.com/meridianlabs-ai/inspect_flow/issues/415)) ([cba3f4d](https://github.com/meridianlabs-ai/inspect_flow/commit/cba3f4d2519dad62cf2833d1fb5af14301ba89a2))
* handle non-Sequence input in matrix arguments ([#414](https://github.com/meridianlabs-ai/inspect_flow/issues/414)) ([bf46b9c](https://github.com/meridianlabs-ai/inspect_flow/commit/bf46b9c625abbd231ea9d86377948d18a4feab23))
* pin inspect-ai version to prevent future breaks ([#413](https://github.com/meridianlabs-ai/inspect_flow/issues/413)) ([6fb1554](https://github.com/meridianlabs-ai/inspect_flow/commit/6fb1554c4a80d8d96a4fa4c046dcc1fcc6ec127b))
* update test to not modify uv.lock ([#409](https://github.com/meridianlabs-ai/inspect_flow/issues/409)) ([a9ab22c](https://github.com/meridianlabs-ai/inspect_flow/commit/a9ab22c5e2d14523779d45eae82fc08c31e525c6))

## [0.1.4](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.1.3...v0.1.4) (2026-01-14)


### Bug Fixes

* add hashes to flow-requirements.txt ([#381](https://github.com/meridianlabs-ai/inspect_flow/issues/381)) ([e870d79](https://github.com/meridianlabs-ai/inspect_flow/commit/e870d7904bcc886d4a3811c79a74abe29f0e2559))
* correctly write flow-requirements.txt to s3 ([#375](https://github.com/meridianlabs-ai/inspect_flow/issues/375)) ([abaecd4](https://github.com/meridianlabs-ai/inspect_flow/commit/abaecd493a962717e7177a9462d6b9a434df429c))
* improved str representation of flow_types ([#382](https://github.com/meridianlabs-ai/inspect_flow/issues/382)) ([eb04076](https://github.com/meridianlabs-ai/inspect_flow/commit/eb0407627c5d2fe08f7e339dbc84e5bfa61903d8))

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
