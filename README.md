# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/meridianlabs-ai/inspect_flow/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                               |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| src/inspect\_flow/\_\_init\_\_.py                  |        8 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/\_\_init\_\_.py            |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/api.py                     |       51 |        0 |       12 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/list\_logs.py              |       40 |       22 |       18 |        2 |     37.93% |12-19, 27-40, 68, 75 |
| src/inspect\_flow/\_cli/\_\_init\_\_.py            |        5 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/config.py                  |       14 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/list.py                    |      362 |      135 |      120 |       23 |     59.34% |53-55, 61, 68, 77, 88-89, 90->92, 101->106, 144, 153-154, 226-228, 232->234, 242, 244, 253, 264, 276-278, 282-291, 295-337, 341-355, 365->368, 374-380, 385-389, 420, 424, 425->427, 439-489, 499-502, 518, 605-606, 611-612 |
| src/inspect\_flow/\_cli/main.py                    |       25 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/options.py                 |       64 |        0 |       16 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/run.py                     |       23 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/store.py                   |      159 |        0 |       46 |        3 |     98.54% |40->42, 264->exit, 373->exit |
| src/inspect\_flow/\_config/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/defaults.py             |       86 |        0 |       44 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/load.py                 |      266 |        4 |      110 |        5 |     97.61% |93->97, 97->99, 100, 102, 106, 227 |
| src/inspect\_flow/\_config/write.py                |       20 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/\_\_init\_\_.py        |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/action.py              |       25 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/display.py             |       33 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_display/full.py                |       56 |        0 |       12 |        1 |     98.53% |  69->exit |
| src/inspect\_flow/\_display/full\_actions.py       |      248 |        8 |       84 |        7 |     95.48% |49-50, 62, 135, 148->159, 151->159, 238-239, 294->exit, 299->exit, 356-357, 375->377 |
| src/inspect\_flow/\_display/path\_progress.py      |       46 |        0 |        8 |        1 |     98.15% |  33->exit |
| src/inspect\_flow/\_display/plain.py               |       51 |        0 |       10 |        1 |     98.36% |  72->exit |
| src/inspect\_flow/\_display/run\_action.py         |       39 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/\_\_init\_\_.py       |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/auto\_dependencies.py |       81 |        0 |       38 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/freeze.py             |       46 |        6 |       16 |        0 |     87.10% |     50-55 |
| src/inspect\_flow/\_launcher/inproc.py             |       13 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/launch.py             |       19 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/pip\_string.py        |       75 |       26 |       28 |        4 |     55.34% |20-24, 87-88, 95-105, 110->112, 115-132 |
| src/inspect\_flow/\_launcher/python\_version.py    |       55 |       14 |       18 |        5 |     68.49% |10, 33-40, 53->51, 60-61, 89-95, 117-119, 125 |
| src/inspect\_flow/\_launcher/venv.py               |      162 |        0 |       58 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/cli.py                  |       33 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/instantiate.py          |      168 |        4 |       80 |        3 |     96.37% |55-57, 92, 258->260 |
| src/inspect\_flow/\_runner/logs.py                 |      119 |        1 |       52 |        4 |     97.08% |43, 171->169, 174->169, 202->197 |
| src/inspect\_flow/\_runner/resolve.py              |       13 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/run.py                  |      155 |        5 |       62 |        4 |     95.85% |188-189, 206, 208, 222, 256->255 |
| src/inspect\_flow/\_runner/task\_log.py            |      136 |        0 |       48 |        0 |    100.00% |           |
| src/inspect\_flow/\_store/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_store/deltalake.py             |      332 |       16 |      110 |       15 |     92.99% |91->exit, 135, 152, 172->171, 178->171, 224-226, 254->260, 257->260, 335-336, 340, 379-381, 389, 391->394, 408, 471->463, 539-540, 544 |
| src/inspect\_flow/\_store/store.py                 |       75 |        1 |       24 |        1 |     97.98% |105, 185->187 |
| src/inspect\_flow/\_types/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/decorator.py             |        7 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/factories.py             |       83 |        0 |       32 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/flow\_types.py           |      200 |        7 |       14 |        1 |     94.39% |70-72, 294-298, 305 |
| src/inspect\_flow/\_types/generated.py             |      251 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/log\_filter.py           |       43 |        5 |       24 |        4 |     86.57% |55, 72, 84, 86-87 |
| src/inspect\_flow/\_types/merge.py                 |       27 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/console.py                |       71 |        6 |       32 |        6 |     88.35% |28->exit, 40-43, 64->73, 89, 92, 106->108 |
| src/inspect\_flow/\_util/constants.py              |        3 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/data.py                   |       25 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/error.py                  |       32 |        2 |       10 |        1 |     92.86% |     32-35 |
| src/inspect\_flow/\_util/list\_util.py             |        8 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/logging.py                |       27 |        0 |        4 |        1 |     96.77% |  32->exit |
| src/inspect\_flow/\_util/logs.py                   |       74 |       11 |       24 |        5 |     81.63% |28-35, 66, 81, 106, 112, 116->109 |
| src/inspect\_flow/\_util/module\_util.py           |       57 |        0 |       22 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/not\_given.py             |        9 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/path\_util.py             |       55 |        1 |       24 |        1 |     97.47% |        29 |
| src/inspect\_flow/\_util/pydantic\_util.py         |       19 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/subprocess\_util.py       |       40 |       14 |       16 |        1 |     69.64% | 26-41, 98 |
| src/inspect\_flow/\_util/util.py                   |        3 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_version.py                     |       13 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/api/\_\_init\_\_.py              |        6 |        0 |        0 |        0 |    100.00% |           |
| **TOTAL**                                          | **4156** |  **288** | **1268** |   **99** | **91.35%** |           |


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