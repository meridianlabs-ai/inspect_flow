# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/meridianlabs-ai/inspect_flow/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                               |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| src/inspect\_flow/\_\_init\_\_.py                  |        9 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/\_\_init\_\_.py            |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/api.py                     |       71 |        1 |       16 |        1 |     97.70% |       148 |
| src/inspect\_flow/\_api/list\_logs.py              |       39 |        3 |       18 |        3 |     89.47% |18, 71, 78 |
| src/inspect\_flow/\_cli/\_\_init\_\_.py            |        5 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/check.py                   |       21 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/config.py                  |       14 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/list.py                    |      513 |      189 |      174 |       32 |     59.39% |60-62, 68, 75, 84, 104-105, 161, 171-172, 247-249, 253-\>255, 263, 265, 274, 285, 303-\>306, 312-\>317, 317-\>322, 337, 355-369, 377, 381, 385-387, 391-400, 408-461, 465, 469-483, 493-\>496, 502-508, 513-517, 555, 559, 560-\>562, 574-626, 642, 649-666, 670, 672, 692, 706-709, 725, 845-846, 859-860 |
| src/inspect\_flow/\_cli/main.py                    |       29 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/options.py                 |       79 |        0 |       16 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/run.py                     |       24 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/step.py                    |      129 |       10 |       52 |       10 |     88.95% |26, 37, 43, 179-\>178, 183, 185, 193, 212, 214, 216, 234 |
| src/inspect\_flow/\_cli/store.py                   |      159 |        0 |       46 |        3 |     98.54% |45-\>47, 256-\>exit, 365-\>exit |
| src/inspect\_flow/\_config/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/defaults.py             |       86 |        0 |       44 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/load.py                 |      270 |        4 |      114 |        5 |     97.66% |93-\>97, 97-\>99, 100, 102, 106, 227 |
| src/inspect\_flow/\_config/write.py                |       20 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/\_\_init\_\_.py        |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/action.py              |       25 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/display.py             |       34 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/full.py                |       56 |        0 |       12 |        1 |     98.53% | 69-\>exit |
| src/inspect\_flow/\_display/full\_actions.py       |      250 |        8 |       84 |        7 |     95.51% |49-50, 62, 142, 155-\>166, 158-\>166, 245-246, 301-\>exit, 306-\>exit, 363-364, 382-\>384 |
| src/inspect\_flow/\_display/path\_progress.py      |       46 |        0 |        8 |        1 |     98.15% | 33-\>exit |
| src/inspect\_flow/\_display/plain.py               |       51 |        0 |       10 |        1 |     98.36% | 72-\>exit |
| src/inspect\_flow/\_display/run\_action.py         |       39 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/\_\_init\_\_.py       |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/auto\_dependencies.py |       81 |        0 |       38 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/freeze.py             |       46 |        6 |       16 |        0 |     87.10% |     50-55 |
| src/inspect\_flow/\_launcher/inproc.py             |       20 |        1 |        4 |        1 |     91.67% |        26 |
| src/inspect\_flow/\_launcher/launch.py             |       27 |        2 |       12 |        2 |     89.74% |    39, 43 |
| src/inspect\_flow/\_launcher/pip\_string.py        |       75 |       26 |       28 |        4 |     55.34% |20-24, 87-88, 95-105, 110-\>112, 115-132 |
| src/inspect\_flow/\_launcher/python\_version.py    |       55 |       14 |       18 |        5 |     68.49% |10, 33-40, 53-\>51, 60-61, 89-95, 117-119, 125 |
| src/inspect\_flow/\_launcher/venv.py               |      167 |        1 |       58 |        0 |     99.56% |        41 |
| src/inspect\_flow/\_runner/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/check.py                |       32 |        1 |       10 |        1 |     95.24% |        23 |
| src/inspect\_flow/\_runner/cli.py                  |       51 |        8 |        0 |        0 |     84.31% |   113-120 |
| src/inspect\_flow/\_runner/instantiate.py          |      186 |        3 |       94 |        4 |     97.50% |64, 67, 108, 282-\>284 |
| src/inspect\_flow/\_runner/logs.py                 |      131 |        1 |       56 |        2 |     98.40% |182, 220-\>214 |
| src/inspect\_flow/\_runner/resolve.py              |       13 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/run.py                  |      168 |        7 |       66 |        5 |     94.02% |177-\>179, 183, 202-203, 220, 236, 275-276 |
| src/inspect\_flow/\_runner/task\_log.py            |      152 |        0 |       56 |        0 |    100.00% |           |
| src/inspect\_flow/\_steps/\_\_init\_\_.py          |        2 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_steps/context.py               |       61 |        2 |       24 |        3 |     94.12% |43, 82, 96-\>103 |
| src/inspect\_flow/\_steps/copy.py                  |       20 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_steps/run.py                   |       50 |        1 |       20 |        1 |     97.14% |        60 |
| src/inspect\_flow/\_steps/step.py                  |       79 |        2 |       28 |        7 |     91.59% |48-\>exit, 53-\>exit, 81-\>exit, 87-\>exit, 91-\>exit, 120, 154 |
| src/inspect\_flow/\_steps/tag.py                   |       24 |        4 |        2 |        0 |     76.92% |     24-32 |
| src/inspect\_flow/\_store/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_store/deltalake.py             |      335 |       16 |      112 |       14 |     93.29% |91-\>exit, 135, 152, 172-\>171, 178-\>171, 224-226, 254-\>260, 257-\>260, 335-336, 340, 379-381, 389, 391-\>394, 408, 544-545, 549 |
| src/inspect\_flow/\_store/store.py                 |       76 |        1 |       24 |        1 |     98.00% |110, 190-\>192 |
| src/inspect\_flow/\_types/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/decorator.py             |        7 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/factories.py             |       83 |        0 |       32 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/flow\_types.py           |      207 |        6 |       20 |        3 |     94.27% |71-73, 292-\>exit, 295-\>exit, 314, 321-322 |
| src/inspect\_flow/\_types/generated.py             |      266 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/log\_filter.py           |       57 |        4 |       28 |        3 |     91.76% |59, 71, 73-74 |
| src/inspect\_flow/\_types/merge.py                 |       27 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/console.py                |       71 |        6 |       32 |        5 |     89.32% |28-\>exit, 40-43, 89, 92, 106-\>108 |
| src/inspect\_flow/\_util/constants.py              |        3 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/data.py                   |       25 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/error.py                  |       50 |        5 |       16 |        0 |     89.39% |     66-70 |
| src/inspect\_flow/\_util/list\_util.py             |        8 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/logging.py                |       27 |        0 |        4 |        1 |     96.77% | 32-\>exit |
| src/inspect\_flow/\_util/logs.py                   |       87 |       11 |       28 |        4 |     85.22% |110, 116, 120-\>113, 150-165 |
| src/inspect\_flow/\_util/module\_util.py           |       57 |        0 |       22 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/not\_given.py             |        9 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/path\_util.py             |       55 |        1 |       24 |        1 |     97.47% |        29 |
| src/inspect\_flow/\_util/pydantic\_util.py         |       19 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/subprocess\_util.py       |       40 |       14 |       16 |        1 |     69.64% | 26-41, 98 |
| src/inspect\_flow/\_util/util.py                   |        3 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_version.py                     |       11 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/api/\_\_init\_\_.py              |       10 |        0 |        0 |        0 |    100.00% |           |
| **TOTAL**                                          | **4942** |  **358** | **1530** |  **132** | **90.98%** |           |


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