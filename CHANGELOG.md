# Changelog

## [0.8.0](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.7.0...v0.8.0) (2026-04-17)


### Features

* flow step command ([#562](https://github.com/meridianlabs-ai/inspect_flow/issues/562)) ([5b0854b](https://github.com/meridianlabs-ai/inspect_flow/commit/5b0854bcf8707452ad949a892caab18a0c196bad))


### Bug Fixes

* add --live option to flow list log ([#630](https://github.com/meridianlabs-ai/inspect_flow/issues/630)) ([b044b6d](https://github.com/meridianlabs-ai/inspect_flow/commit/b044b6d93bdf1d33dbe9283473d94f717cdd003a))
* add --provenance flag to flow list log ([#649](https://github.com/meridianlabs-ai/inspect_flow/issues/649)) ([e0c28bd](https://github.com/meridianlabs-ai/inspect_flow/commit/e0c28bd957016294011f3a302fca518e5c690f9f))
* add --tag filtering support to flow list log ([#626](https://github.com/meridianlabs-ai/inspect_flow/issues/626)) ([908af10](https://github.com/meridianlabs-ai/inspect_flow/commit/908af103673c6822830f73971954324101e7d0e8))
* add numbering to flow list log ([#673](https://github.com/meridianlabs-ai/inspect_flow/issues/673)) ([ec57fd7](https://github.com/meridianlabs-ai/inspect_flow/commit/ec57fd7428698c12a0151009df3b53e7895ab5d4))
* add tags column to task display ([#616](https://github.com/meridianlabs-ai/inspect_flow/issues/616)) ([4f4794d](https://github.com/meridianlabs-ai/inspect_flow/commit/4f4794d3a3449423e3c946a56f9628ac3cf222ce))
* add tags to flow list log ([#629](https://github.com/meridianlabs-ai/inspect_flow/issues/629)) ([04f0f70](https://github.com/meridianlabs-ai/inspect_flow/commit/04f0f702c97ac77432d9206036d076c028f9b618))
* better handling of SSO refresh errors ([#627](https://github.com/meridianlabs-ai/inspect_flow/issues/627)) ([6f6b097](https://github.com/meridianlabs-ai/inspect_flow/commit/6f6b097a51576b3bb228cc84bb9ad1cca50750de))
* consistent --store param ([#636](https://github.com/meridianlabs-ai/inspect_flow/issues/636)) ([158ae48](https://github.com/meridianlabs-ai/inspect_flow/commit/158ae480de43254c30632941c8e6ea246f6936f2))
* flow check command improvements ([#614](https://github.com/meridianlabs-ai/inspect_flow/issues/614)) ([d337fe5](https://github.com/meridianlabs-ai/inspect_flow/commit/d337fe556c71eb72f482b3da522d08cfeba8329d))
* flow list log default to multiline format ([#628](https://github.com/meridianlabs-ai/inspect_flow/issues/628)) ([6cfbab4](https://github.com/meridianlabs-ai/inspect_flow/commit/6cfbab45fef57fdd75ad855a6fa04b37a5462c70))
* improve --set help text ([#622](https://github.com/meridianlabs-ai/inspect_flow/issues/622)) ([8859d5d](https://github.com/meridianlabs-ai/inspect_flow/commit/8859d5d0ed6aa3df1ecddbae41e7540e46b5ac50))
* improve and document filter behavior ([#632](https://github.com/meridianlabs-ai/inspect_flow/issues/632)) ([b069e2f](https://github.com/meridianlabs-ai/inspect_flow/commit/b069e2fc4988a6cd23ff3c738846fa7f251116ea))
* improve handling of KeyboardInterrupt during eval_set ([#607](https://github.com/meridianlabs-ai/inspect_flow/issues/607)) ([ebf3789](https://github.com/meridianlabs-ai/inspect_flow/commit/ebf378951e8b16ae82b2cb42f46355e1695f2e54))
* improve list log performance by reading samples async ([#609](https://github.com/meridianlabs-ai/inspect_flow/issues/609)) ([06f4813](https://github.com/meridianlabs-ai/inspect_flow/commit/06f481344c7e268e8830f93649c22c566a912528))
* improve performance of adding logs to store ([#663](https://github.com/meridianlabs-ai/inspect_flow/issues/663)) ([bb91abc](https://github.com/meridianlabs-ai/inspect_flow/commit/bb91abcff9fd38f30e43e62510ba458626f50f6f))
* improved flow list log output format ([#638](https://github.com/meridianlabs-ai/inspect_flow/issues/638)) ([37b6f3f](https://github.com/meridianlabs-ai/inspect_flow/commit/37b6f3fd7b58207a36886696f85f11de23f0a05a))
* including files with just [@step](https://github.com/step) function ([#623](https://github.com/meridianlabs-ai/inspect_flow/issues/623)) ([922a9d1](https://github.com/meridianlabs-ai/inspect_flow/commit/922a9d1d42b33750f773c1010cfb16ded96314b5))
* installing git+ additional depcencies ([#672](https://github.com/meridianlabs-ai/inspect_flow/issues/672)) ([c0fb27a](https://github.com/meridianlabs-ai/inspect_flow/commit/c0fb27afb204b562610745f31ab77287baa1b9e0))
* move duplicate logs before unnexpected logs in flow check output ([#665](https://github.com/meridianlabs-ai/inspect_flow/issues/665)) ([d9f9f10](https://github.com/meridianlabs-ai/inspect_flow/commit/d9f9f1054ee636b559f35aac1af723cfd170c4f9))
* remove unused _StepDecorator ([#670](https://github.com/meridianlabs-ai/inspect_flow/issues/670)) ([ae3a829](https://github.com/meridianlabs-ai/inspect_flow/commit/ae3a82949e7c762a0d401cc6b8857101d32a8e0c))
* return results from check API method ([#615](https://github.com/meridianlabs-ai/inspect_flow/issues/615)) ([c2f9318](https://github.com/meridianlabs-ai/inspect_flow/commit/c2f93188de388e3e84f91dc6e4b5b7d536a94413))
* steps write new logs to store ([#625](https://github.com/meridianlabs-ai/inspect_flow/issues/625)) ([499ebd6](https://github.com/meridianlabs-ai/inspect_flow/commit/499ebd62e90ad1afc545c68f02ee88f4b14c14ba))
* support factory instantiation in venv mode ([#624](https://github.com/meridianlabs-ai/inspect_flow/issues/624)) ([bc90db4](https://github.com/meridianlabs-ai/inspect_flow/commit/bc90db4bfd39c7272a81176955dffd95c2aca06d))
* task differentiator when FlowFactory args are used ([#647](https://github.com/meridianlabs-ai/inspect_flow/issues/647)) ([90a119c](https://github.com/meridianlabs-ai/inspect_flow/commit/90a119ccc74309e3a8308e14d096441d7cd680fd))
* update display to show summary at bottom of box ([#639](https://github.com/meridianlabs-ai/inspect_flow/issues/639)) ([8124c1b](https://github.com/meridianlabs-ai/inspect_flow/commit/8124c1b4b3ed61546c78583cd8bf1fcd1391133c))


### Documentation

* add documentation for flow steps and flow check ([#667](https://github.com/meridianlabs-ai/inspect_flow/issues/667)) ([2ea1895](https://github.com/meridianlabs-ai/inspect_flow/commit/2ea1895daa148943dcdfb43a502263b50dc9d63a))
* clarify list log falls back to default store when PATH not provided ([#634](https://github.com/meridianlabs-ai/inspect_flow/issues/634)) ([c60f83a](https://github.com/meridianlabs-ai/inspect_flow/commit/c60f83a341b80148a6500edaaa2e329877f671bf))

## [0.7.0](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.6.0...v0.7.0) (2026-03-24)


### Features

* FlowFactory to provide type checking of factory argumnets ([#580](https://github.com/meridianlabs-ai/inspect_flow/issues/580)) ([8403977](https://github.com/meridianlabs-ai/inspect_flow/commit/8403977d82f05bec12ba595e345699708e098ffe))
* list log command ([#575](https://github.com/meridianlabs-ai/inspect_flow/issues/575)) ([87e6b28](https://github.com/meridianlabs-ai/inspect_flow/commit/87e6b2869dadab511d689843b1e5ab6ac754e3b9))
* store_read and store_write flags. Default store_read off. ([#585](https://github.com/meridianlabs-ai/inspect_flow/issues/585)) ([d9f75b6](https://github.com/meridianlabs-ai/inspect_flow/commit/d9f75b6c0e4f6d078a56b4141a344fb2a7c38875))


### Bug Fixes

* add support for tags on FlowTask ([#593](https://github.com/meridianlabs-ai/inspect_flow/issues/593)) ([4d070d7](https://github.com/meridianlabs-ai/inspect_flow/commit/4d070d71ad8c3291571a3cadc78e1432ea6fc422))
* add viewer url column to flow list log ([#586](https://github.com/meridianlabs-ai/inspect_flow/issues/586)) ([c877ecb](https://github.com/meridianlabs-ai/inspect_flow/commit/c877ecb51a36418f128462762020e3e683a24dcc))
* count of samples in log when results is missing or invalidated ([#598](https://github.com/meridianlabs-ai/inspect_flow/issues/598)) ([8bca19e](https://github.com/meridianlabs-ai/inspect_flow/commit/8bca19eeb9bd0b8463bf8bab977155dfe0609a0c))
* do not output file:// prefix in list log tree format ([#581](https://github.com/meridianlabs-ai/inspect_flow/issues/581)) ([3fe7859](https://github.com/meridianlabs-ai/inspect_flow/commit/3fe7859a94cfbdb31c1b005f5ca05f79f41aad64))
* ensure inspect_ai log level is set correctly before calling eval_set ([#576](https://github.com/meridianlabs-ai/inspect_flow/issues/576)) ([78f2923](https://github.com/meridianlabs-ai/inspect_flow/commit/78f292315380358f67ec950e0b1e0c24dd3f93eb))
* improved output for store usage ([#591](https://github.com/meridianlabs-ai/inspect_flow/issues/591)) ([dc38b34](https://github.com/meridianlabs-ai/inspect_flow/commit/dc38b34d0c524d8321c0bbfee882f31364035b20))
* preserve task name when provided ([#563](https://github.com/meridianlabs-ai/inspect_flow/issues/563)) ([a02da20](https://github.com/meridianlabs-ai/inspect_flow/commit/a02da20a5d8b3deebe56b50021717f3202f3f8dd))
* resolve relative paths on import ([#597](https://github.com/meridianlabs-ai/inspect_flow/issues/597)) ([e5d3268](https://github.com/meridianlabs-ai/inspect_flow/commit/e5d32686b5db73e46517cc46abd6be89172bfa38))
* set default display to rich ([#577](https://github.com/meridianlabs-ai/inspect_flow/issues/577)) ([77ad180](https://github.com/meridianlabs-ai/inspect_flow/commit/77ad1804b1601c4cd57f714fd93a67e57d7761e7))
* support multiple --store-filter ([#596](https://github.com/meridianlabs-ai/inspect_flow/issues/596)) ([617c9be](https://github.com/meridianlabs-ai/inspect_flow/commit/617c9be8a3e518811e4897d915720899c6646cdf))
* support multiple log filters ([#592](https://github.com/meridianlabs-ai/inspect_flow/issues/592)) ([1dcdf32](https://github.com/meridianlabs-ai/inspect_flow/commit/1dcdf327d471471745fe22643f0f371a6ad7f03a))
* update to new embedded_viewer path ([#590](https://github.com/meridianlabs-ai/inspect_flow/issues/590)) ([ebfbe8b](https://github.com/meridianlabs-ai/inspect_flow/commit/ebfbe8b31faab1be6c0099c60b853b325648fa75))


### Documentation

* update docs for PRs [#577](https://github.com/meridianlabs-ai/inspect_flow/issues/577), [#575](https://github.com/meridianlabs-ai/inspect_flow/issues/575), [#563](https://github.com/meridianlabs-ai/inspect_flow/issues/563), [#552](https://github.com/meridianlabs-ai/inspect_flow/issues/552), [#551](https://github.com/meridianlabs-ai/inspect_flow/issues/551), [#550](https://github.com/meridianlabs-ai/inspect_flow/issues/550), [#580](https://github.com/meridianlabs-ai/inspect_flow/issues/580) ([#584](https://github.com/meridianlabs-ai/inspect_flow/issues/584)) ([5b0646d](https://github.com/meridianlabs-ai/inspect_flow/commit/5b0646d1bec7beb3143d9dd67a933f8f0c31d666))
* update docs for PRs [#592](https://github.com/meridianlabs-ai/inspect_flow/issues/592), [#593](https://github.com/meridianlabs-ai/inspect_flow/issues/593) ([#595](https://github.com/meridianlabs-ai/inspect_flow/issues/595)) ([a9214cb](https://github.com/meridianlabs-ai/inspect_flow/commit/a9214cb56cb4a161ae0f30c8bd9188f9a3372cf3))
* update docs for store_read/store_write changes ([#585](https://github.com/meridianlabs-ai/inspect_flow/issues/585)) ([#588](https://github.com/meridianlabs-ai/inspect_flow/issues/588)) ([24a173b](https://github.com/meridianlabs-ai/inspect_flow/commit/24a173b849b89498117a829f2af7f64af9c0f367))

## [0.6.0](https://github.com/meridianlabs-ai/inspect_flow/compare/v0.5.0...v0.6.0) (2026-03-16)


### Features

* store filtering ([#552](https://github.com/meridianlabs-ai/inspect_flow/issues/552)) ([e197b1c](https://github.com/meridianlabs-ai/inspect_flow/commit/e197b1cf5262d16849ce77ea555f6ad4df6318f1))


### Bug Fixes

* --copy-from support for s3: paths ([#551](https://github.com/meridianlabs-ai/inspect_flow/issues/551)) ([e1fe49a](https://github.com/meridianlabs-ai/inspect_flow/commit/e1fe49a3f5a84fa4da5ba4161e74f946c557aee8))
* add embed_viewer location to output ([#550](https://github.com/meridianlabs-ai/inspect_flow/issues/550)) ([7a87b43](https://github.com/meridianlabs-ai/inspect_flow/commit/7a87b435bba41661c7bfb22d4503bb0fda49636a))
* add support for embed_viewer option ([#544](https://github.com/meridianlabs-ai/inspect_flow/issues/544)) ([d310ef5](https://github.com/meridianlabs-ai/inspect_flow/commit/d310ef50fb7ab508d326a8786d48e7b7dce5b810))
* improve output when both bundle and embed_viewer are set ([#553](https://github.com/meridianlabs-ai/inspect_flow/issues/553)) ([2b285a9](https://github.com/meridianlabs-ai/inspect_flow/commit/2b285a9ae69c1ded1936973925a939c16d65fa0c))
* print paths using console wrapping so they are copyable ([#554](https://github.com/meridianlabs-ai/inspect_flow/issues/554)) ([2ea750d](https://github.com/meridianlabs-ai/inspect_flow/commit/2ea750deb3e439331c488cc655238d8d3071c463))
* re-set moto env vars before each S3 test ([#543](https://github.com/meridianlabs-ai/inspect_flow/issues/543)) ([216fdeb](https://github.com/meridianlabs-ai/inspect_flow/commit/216fdeb585d6bd6c9a97950129471e3c3be11b33))
* Update dependencies (includes embed_viewer fix) ([#561](https://github.com/meridianlabs-ai/inspect_flow/issues/561)) ([27d4a4b](https://github.com/meridianlabs-ai/inspect_flow/commit/27d4a4b48dbf4532144db1fbd6281c559244d896))
* update inspect and support new fields and limit matrixing ([#538](https://github.com/meridianlabs-ai/inspect_flow/issues/538)) ([553e6c1](https://github.com/meridianlabs-ai/inspect_flow/commit/553e6c1941d631fcd98ff09a21d393626a7002e5))
* upgrade inspect-ai and fix absolute path issue ([#542](https://github.com/meridianlabs-ai/inspect_flow/issues/542)) ([a47cbd3](https://github.com/meridianlabs-ai/inspect_flow/commit/a47cbd3b31cc256da1b50d5f343ad5edb5d992de))


### Documentation

* add documentation for matrix limits, function configs, and YAML support ([#540](https://github.com/meridianlabs-ai/inspect_flow/issues/540)) ([7a2ffc0](https://github.com/meridianlabs-ai/inspect_flow/commit/7a2ffc024aab656a1aba425d9a9fdf173d064440))
* document embed_viewer option in viewer bundling section ([#546](https://github.com/meridianlabs-ai/inspect_flow/issues/546)) ([dd53edd](https://github.com/meridianlabs-ai/inspect_flow/commit/dd53eddbc8060d289f7c754c8b1460eff53870a9))

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
