# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/meridianlabs-ai/inspect_flow/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                               |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| src/inspect\_flow/\_\_init\_\_.py                  |       10 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/\_\_init\_\_.py            |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/api.py                     |       90 |        1 |       18 |        1 |     98.15% |       197 |
| src/inspect\_flow/\_api/list\_logs.py              |       39 |        3 |       18 |        3 |     89.47% |18, 71, 78 |
| src/inspect\_flow/\_cli/\_\_init\_\_.py            |        5 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/check.py                   |       29 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/config.py                  |       20 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/constants.py               |       54 |        3 |       24 |        4 |     91.03% |29, 37-\>39, 44, 62 |
| src/inspect\_flow/\_cli/json\_output.py            |       34 |        0 |        6 |        1 |     97.50% |   61-\>63 |
| src/inspect\_flow/\_cli/list.py                    |      605 |      152 |      210 |       40 |     71.53% |70-72, 78, 85, 94, 114-115, 171, 177, 179, 186, 194-195, 283-285, 289-\>291, 300, 302, 311, 322, 355, 368-\>371, 374-\>382, 378-\>380, 406-\>410, 422, 444-458, 466, 470, 484-491, 533, 539-543, 548-549, 564-578, 588-\>591, 598, 603, 610, 654, 659-\>661, 673-731, 747, 754-771, 775, 795, 809-812, 844, 973-974, 987-988 |
| src/inspect\_flow/\_cli/main.py                    |       34 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/options.py                 |       81 |        0 |       16 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/run.py                     |       37 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/step.py                    |      195 |       17 |       84 |       19 |     87.10% |27, 40, 43, 53-54, 76, 85, 91-\>98, 93-\>92, 95, 102, 108, 143-\>146, 146-\>exit, 293-\>292, 298, 300, 308, 330, 332, 334, 352 |
| src/inspect\_flow/\_cli/store.py                   |      177 |        0 |       52 |        3 |     98.69% |49-\>51, 260-\>exit, 400-\>exit |
| src/inspect\_flow/\_config/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/defaults.py             |       86 |        0 |       44 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/load.py                 |      271 |        4 |      114 |        5 |     97.66% |98-\>102, 102-\>104, 105, 107, 111, 248 |
| src/inspect\_flow/\_config/write.py                |       20 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/\_\_init\_\_.py        |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/action.py              |       25 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/display.py             |       60 |        0 |       16 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/full.py                |       56 |        0 |       12 |        1 |     98.53% | 69-\>exit |
| src/inspect\_flow/\_display/full\_actions.py       |      257 |        8 |       90 |        7 |     95.68% |49-50, 62, 142, 155-\>166, 158-\>166, 245-246, 309-\>exit, 314-\>exit, 371-372, 390-\>392 |
| src/inspect\_flow/\_display/no.py                  |       32 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/path\_progress.py      |       46 |        0 |        8 |        1 |     98.15% | 33-\>exit |
| src/inspect\_flow/\_display/plain.py               |       50 |        0 |       10 |        1 |     98.33% | 70-\>exit |
| src/inspect\_flow/\_display/run\_action.py         |       39 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/\_\_init\_\_.py       |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/auto\_dependencies.py |       83 |        0 |       38 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/freeze.py             |       47 |        6 |       16 |        0 |     87.30% |     57-62 |
| src/inspect\_flow/\_launcher/inproc.py             |       25 |        2 |        6 |        2 |     87.10% |    26, 33 |
| src/inspect\_flow/\_launcher/launch.py             |       42 |        1 |       14 |        1 |     96.43% |        66 |
| src/inspect\_flow/\_launcher/pip\_string.py        |       75 |       26 |       28 |        4 |     55.34% |20-24, 87-88, 95-105, 110-\>112, 115-132 |
| src/inspect\_flow/\_launcher/python\_version.py    |       55 |       14 |       18 |        5 |     68.49% |10, 33-40, 53-\>51, 60-61, 89-95, 117-119, 125 |
| src/inspect\_flow/\_launcher/venv.py               |      221 |        3 |       82 |        3 |     98.02% |18, 286, 299 |
| src/inspect\_flow/\_runner/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/check.py                |       35 |        1 |       10 |        1 |     95.56% |        23 |
| src/inspect\_flow/\_runner/cli.py                  |       72 |       11 |        4 |        2 |     82.89% |47-48, 119-123, 146-149 |
| src/inspect\_flow/\_runner/instantiate.py          |      245 |        3 |      112 |        3 |     98.32% |74, 302-303, 394-\>396 |
| src/inspect\_flow/\_runner/logs.py                 |      141 |        1 |       56 |        2 |     98.48% |216, 254-\>248 |
| src/inspect\_flow/\_runner/resolve.py              |       13 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/run.py                  |      238 |       12 |       90 |       10 |     92.68% |244-\>246, 252, 270-271, 288, 304, 345-346, 363, 385-\>382, 386-\>385, 388, 394, 397-398 |
| src/inspect\_flow/\_runner/task\_log.py            |      159 |        0 |       60 |        0 |    100.00% |           |
| src/inspect\_flow/\_steps/\_\_init\_\_.py          |        2 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_steps/context.py               |       60 |        0 |       14 |        0 |    100.00% |           |
| src/inspect\_flow/\_steps/copy.py                  |       27 |        0 |       10 |        1 |     97.30% |   52-\>54 |
| src/inspect\_flow/\_steps/run.py                   |       55 |        1 |       26 |        2 |     96.30% |63, 109-\>exit |
| src/inspect\_flow/\_steps/scan.py                  |       82 |       16 |       28 |        9 |     71.82% |168-178, 183, 188-\>198, 193-\>198, 206-207, 213, 219, 241, 245 |
| src/inspect\_flow/\_steps/scan\_options.py         |       11 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_steps/step.py                  |       74 |        2 |       18 |        2 |     95.65% |  135, 152 |
| src/inspect\_flow/\_steps/tag.py                   |       28 |        4 |        6 |        0 |     82.35% |     24-32 |
| src/inspect\_flow/\_store/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_store/deltalake.py             |      340 |       16 |      116 |       14 |     93.42% |93-\>exit, 163, 186-\>185, 192-\>185, 238-240, 268-\>274, 271-\>274, 355-356, 360, 399-401, 409, 411-\>414, 428, 536, 584-585, 589 |
| src/inspect\_flow/\_store/store.py                 |       76 |        1 |       24 |        1 |     98.00% |110, 190-\>192 |
| src/inspect\_flow/\_types/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/after\_instantiate.py    |       22 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/decorator.py             |        7 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/factories.py             |       83 |        0 |       32 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/flow\_types.py           |      222 |        4 |       20 |        3 |     95.45% |72-74, 301-\>exit, 304-\>exit, 323 |
| src/inspect\_flow/\_types/generated.py             |      272 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/log\_filter.py           |       57 |        4 |       28 |        3 |     91.76% |59, 71, 73-74 |
| src/inspect\_flow/\_types/merge.py                 |       27 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/console.py                |       71 |        6 |       32 |        5 |     89.32% |28-\>exit, 40-43, 89, 92, 106-\>108 |
| src/inspect\_flow/\_util/constants.py              |        4 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/data.py                   |       25 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/error.py                  |       53 |        7 |       18 |        1 |     85.92% |40-41, 69-73 |
| src/inspect\_flow/\_util/list\_util.py             |        8 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/logging.py                |       27 |        0 |        4 |        1 |     96.77% | 32-\>exit |
| src/inspect\_flow/\_util/logs.py                   |       89 |       11 |       28 |        4 |     85.47% |117, 123, 127-\>120, 157-172 |
| src/inspect\_flow/\_util/module\_util.py           |       57 |        0 |       22 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/not\_given.py             |        9 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/path\_util.py             |       55 |        1 |       24 |        1 |     97.47% |        29 |
| src/inspect\_flow/\_util/pydantic\_util.py         |       19 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/subprocess\_util.py       |       54 |       10 |       20 |        2 |     83.78% |85-94, 151 |
| src/inspect\_flow/\_util/terminal.py               |       12 |        6 |        0 |        0 |     50.00% |9-12, 19-20 |
| src/inspect\_flow/\_util/util.py                   |       14 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_version.py                     |       11 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/api/\_\_init\_\_.py              |       11 |        0 |        0 |        0 |    100.00% |           |
| **TOTAL**                                          | **5767** |  **357** | **1786** |  **168** | **91.99%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/meridianlabs-ai/inspect_flow/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/meridianlabs-ai/inspect_flow/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/meridianlabs-ai/inspect_flow/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/meridianlabs-ai/inspect_flow/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fmeridianlabs-ai%2Finspect_flow%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/meridianlabs-ai/inspect_flow/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.