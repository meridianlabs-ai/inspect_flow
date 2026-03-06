# Changelog

## [0.5.0](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.4.1...v0.5.0) (2026-03-06)


### Features

* add --resume flag to reuse previous log dir ([#532](https://github.com/meridianlabs-ai/inspect_flow/issues/532)) ([a2d9ea9](https://github.com/meridianlabs-ai/inspect_flow/commit/a2d9ea92c81a75acd227cbe1f95b44822058e539))


### Bug Fixes

* --log-dir-create-unique creates subdir with the current timestamp ([#526](https://github.com/meridianlabs-ai/inspect_flow/issues/526)) ([392e34e](https://github.com/meridianlabs-ai/inspect_flow/commit/392e34e5d69df4f7d47f618cf2806d3a2a43cd85))
* add DATETIME substitution ([#527](https://github.com/meridianlabs-ai/inspect_flow/issues/527)) ([2ad8104](https://github.com/meridianlabs-ai/inspect_flow/commit/2ad81040b70e14dfdba4dbeecea06d4c232b1ce6))
* add task name as context to display on instantiation errors ([#536](https://github.com/meridianlabs-ai/inspect_flow/issues/536)) ([ad14540](https://github.com/meridianlabs-ai/inspect_flow/commit/ad14540772867780b107bbdf01ace6e18ad9c515))
* ensure bundle url ends with a / ([#515](https://github.com/meridianlabs-ai/inspect_flow/issues/515)) ([f04a04a](https://github.com/meridianlabs-ai/inspect_flow/commit/f04a04a3d4219de24f34cfebdc6f1a43810a396c))
* s3 store paths with trailing slash ([#535](https://github.com/meridianlabs-ai/inspect_flow/issues/535)) ([8c6568a](https://github.com/meridianlabs-ai/inspect_flow/commit/8c6568a245e585579e2d2b1568fb7d85497a94b1))
* support reading default model from env var ([#524](https://github.com/meridianlabs-ai/inspect_flow/issues/524)) ([e4eafe9](https://github.com/meridianlabs-ai/inspect_flow/commit/e4eafe959af1f19a924238643a9ded02650c67dc))
* upgrade packages and import TASK_IDENTIFIER_VERSION from inspect ([#513](https://github.com/meridianlabs-ai/inspect_flow/issues/513)) ([5a2f846](https://github.com/meridianlabs-ai/inspect_flow/commit/5a2f8464fd82b366d7b2f7816c9688fe3003788e))
* use absolute URLs for README images so they render on PyPI ([#530](https://github.com/meridianlabs-ai/inspect_flow/issues/530)) ([f6f8f35](https://github.com/meridianlabs-ai/inspect_flow/commit/f6f8f35347f3daa47df31db274c7b1fb4ec8e9ac))


### Documentation

* add llms.txt and llms-full.txt generation ([#517](https://github.com/meridianlabs-ai/inspect_flow/issues/517)) ([959cf28](https://github.com/meridianlabs-ai/inspect_flow/commit/959cf28d40855ec6024b7413113fa23dff29d079))
* improve API reference docs ([#523](https://github.com/meridianlabs-ai/inspect_flow/issues/523)) ([f1fc94f](https://github.com/meridianlabs-ai/inspect_flow/commit/f1fc94f4d4fa3e8277fefc7c017e104a0acb6e0e))
* update docs for --resume, {DATETIME}, and --log-dir-create-unique ([#529](https://github.com/meridianlabs-ai/inspect_flow/issues/529)) ([f32fa5c](https://github.com/meridianlabs-ai/inspect_flow/commit/f32fa5c6540892f2286a893db1b457479185fabf))

## [0.4.1](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.4.0...v0.4.1) (2026-02-20)


### Bug Fixes

* add docstring to DisplayType for quarto docs build ([#504](https://github.com/meridianlabs-ai/inspect_flow/issues/504)) ([dfdf661](https://github.com/meridianlabs-ai/inspect_flow/commit/dfdf661df75c2f3f4c42c9e9fe87c3be47f3939f))
* compile with conflicting git urls ([#508](https://github.com/meridianlabs-ai/inspect_flow/issues/508)) ([b0f3324](https://github.com/meridianlabs-ai/inspect_flow/commit/b0f33243e02462d9d7b222d32cb7a4652b87ea34))
* default to have eval_set use the flow log_level if not explicitly set in FlowOptions ([#507](https://github.com/meridianlabs-ai/inspect_flow/issues/507)) ([8bf12d5](https://github.com/meridianlabs-ai/inspect_flow/commit/8bf12d53a5de2775a7205add3b0d88168a376ad5))
* tests to handle inspect_ai installed from git ([#506](https://github.com/meridianlabs-ai/inspect_flow/issues/506)) ([26b5925](https://github.com/meridianlabs-ai/inspect_flow/commit/26b59254f87c4d28f445235a72288c2978464cd6))

## [0.4.0](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.3.0...v0.4.0) (2026-02-19)


### Features

* flow store to enable log reuse across directories ([#340](https://github.com/meridianlabs-ai/inspect_flow/issues/340)) ([bc5d993](https://github.com/meridianlabs-ai/inspect_flow/commit/bc5d9935c63cef984edcdc0f6ccc6a61ee6ea716))


### Bug Fixes

* add progress console output for loading tasks ([#476](https://github.com/meridianlabs-ai/inspect_flow/issues/476)) ([763023d](https://github.com/meridianlabs-ai/inspect_flow/commit/763023d6d0a3b0b644ee0e6096a592fbb8702a81))
* avoid extra output on Ctrl+C ([#475](https://github.com/meridianlabs-ai/inspect_flow/issues/475)) ([638bdf6](https://github.com/meridianlabs-ai/inspect_flow/commit/638bdf6d8733e9509cfa39bff9488d580adaf5b6))
* display_type set in options ([#473](https://github.com/meridianlabs-ai/inspect_flow/issues/473)) ([0fd9213](https://github.com/meridianlabs-ai/inspect_flow/commit/0fd92133e2f1e2f2615fc2eef3fa138e3c91be63))

## [0.3.0](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.2.2...v0.3.0) (2026-02-03)


### Features

* improved console output ([#466](https://github.com/meridianlabs-ai/inspect_flow/issues/466)) ([247725f](https://github.com/meridianlabs-ai/inspect_flow/commit/247725fd141182b20b568733c6bf7f1c71e841f9))


### Bug Fixes

* _flow.py should not include itself when loaded directly ([#467](https://github.com/meridianlabs-ai/inspect_flow/issues/467)) ([3e26333](https://github.com/meridianlabs-ai/inspect_flow/commit/3e2633372f1950b0c6f86ae0f4de51843d293f18)), closes [#465](https://github.com/meridianlabs-ai/inspect_flow/issues/465)
* log-dir-create-unique corrected handling of paths ending in / ([#451](https://github.com/meridianlabs-ai/inspect_flow/issues/451)) ([2f5b3ab](https://github.com/meridianlabs-ai/inspect_flow/commit/2f5b3ab9744d86a9a697d65de29391f69dba43a3))
* test bundle_dir location and stricter type checking ([#463](https://github.com/meridianlabs-ai/inspect_flow/issues/463)) ([11f2328](https://github.com/meridianlabs-ai/inspect_flow/commit/11f232806c1a3292433f8401918d4865ad5357fc))
* use rich display of exception traceback ([#459](https://github.com/meridianlabs-ai/inspect_flow/issues/459)) ([70d0ff7](https://github.com/meridianlabs-ai/inspect_flow/commit/70d0ff743b4820e25ed2b9a77d8aa72d2a4de8db))

## [0.2.2](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.2.1...v0.2.2) (2026-01-26)


### Bug Fixes

* remove duplicated inspect_ai code ([#444](https://github.com/meridianlabs-ai/inspect_flow/issues/444)) ([c6c141c](https://github.com/meridianlabs-ai/inspect_flow/commit/c6c141cad42f997a2b128add00688e9c4a2024ec))
* use inspect-ai load_tasks to ensure task path is captured correctly ([#441](https://github.com/meridianlabs-ai/inspect_flow/issues/441)) ([b34e303](https://github.com/meridianlabs-ai/inspect_flow/commit/b34e303c7e504402c894ffc8b92539d18e94914a))

## [0.2.1](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.2.0...v0.2.1) (2026-01-23)


### Bug Fixes

* apply substitutions, defaults, and call [@after](https://github.com/after)_load functions after overrides ([#440](https://github.com/meridianlabs-ai/inspect_flow/issues/440)) ([0b507c9](https://github.com/meridianlabs-ai/inspect_flow/commit/0b507c96d26adf713636b7484535c9fe476e57c6))
* enable relative imports for local file ([#436](https://github.com/meridianlabs-ai/inspect_flow/issues/436)) ([50d8a43](https://github.com/meridianlabs-ai/inspect_flow/commit/50d8a43920c9d7c5c66e7da5a99841ee73b1798e))
* RuntimeError when calling run while loading a spec file ([#434](https://github.com/meridianlabs-ai/inspect_flow/issues/434)) ([411aa08](https://github.com/meridianlabs-ai/inspect_flow/commit/411aa08ac5ff52573501c61d2ff794bd7c78b1db))


### Documentation

* document extra_args for per-task customization ([#439](https://github.com/meridianlabs-ai/inspect_flow/issues/439)) ([8210b3a](https://github.com/meridianlabs-ai/inspect_flow/commit/8210b3a6dcfed85d282937304e37a25afc04d722))

## [0.2.0](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.1.4...v0.2.0) (2026-01-22)


### Features

* default to running inproc and support for inspect-ai types ([#421](https://github.com/meridianlabs-ai/inspect_flow/issues/421)) ([0ad7ff1](https://github.com/meridianlabs-ai/inspect_flow/commit/0ad7ff1))
* support specifying tools for a FlowTask ([#401](https://github.com/meridianlabs-ai/inspect_flow/issues/401)) ([3a5903a](https://github.com/meridianlabs-ai/inspect_flow/commit/3a5903a3077c4850c5664976ee4615b7a6935a4c))


### Bug Fixes

* add --log-dir-allow-dirty flag ([#416](https://github.com/meridianlabs-ai/inspect_flow/issues/416)) ([a27f79d](https://github.com/meridianlabs-ai/inspect_flow/commit/a27f79d936b62996a8936890104d3e93306e5815))
* Allow including flow spec objects ([#420](https://github.com/meridianlabs-ai/inspect_flow/issues/420)) ([52dade6](https://github.com/meridianlabs-ai/inspect_flow/commit/52dade680a09d2df7f3b8905770e3b21aa9bcbe2))
* auto collect dependencies from INSPECT_EVAL_MODEL ([#415](https://github.com/meridianlabs-ai/inspect_flow/issues/415)) ([cba3f4d](https://github.com/meridianlabs-ai/inspect_flow/commit/cba3f4d2519dad62cf2833d1fb5af14301ba89a2))
* Deduplicate pip freeze output ([#422](https://github.com/meridianlabs-ai/inspect_flow/issues/422)) ([a2fa987](https://github.com/meridianlabs-ai/inspect_flow/commit/a2fa987eca2ea31b8385ea92fe0cb2922b5dfc31))
* handle non-Sequence input in matrix arguments ([#414](https://github.com/meridianlabs-ai/inspect_flow/issues/414)) ([bf46b9c](https://github.com/meridianlabs-ai/inspect_flow/commit/bf46b9c625abbd231ea9d86377948d18a4feab23))
* update test to not modify uv.lock ([#409](https://github.com/meridianlabs-ai/inspect_flow/issues/409)) ([a9ab22c](https://github.com/meridianlabs-ai/inspect_flow/commit/a9ab22c5e2d14523779d45eae82fc08c31e525c6))


### Documentation

* inproc execution mode updates ([#433](https://github.com/meridianlabs-ai/inspect_flow/issues/433)) ([8c56f9f](https://github.com/meridianlabs-ai/inspect_flow/commit/8c56f9f9790957a01a0188927634f67fb83a40f3))
* update defaults.qmd for FlowSpec includes ([#425](https://github.com/meridianlabs-ai/inspect_flow/issues/425)) ([c979e0b](https://github.com/meridianlabs-ai/inspect_flow/commit/c979e0bd6072f4c85fb49b56e719b6eb5dc25fdc))

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
