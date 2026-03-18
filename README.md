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
| src/inspect\_flow/\_cli/list.py                    |      323 |      128 |      108 |       19 |     57.08% |47-48, 49->51, 60->65, 103, 111-112, 178-180, 184->186, 193, 201, 212, 224-226, 230-239, 243-285, 289-303, 313->316, 322-328, 333-337, 368, 372, 373->375, 387-437, 447-450, 466, 549-550, 555-556 |
| src/inspect\_flow/\_cli/main.py                    |       25 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/options.py                 |       62 |        0 |       16 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/run.py                     |       23 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/store.py                   |      159 |        0 |       46 |        3 |     98.54% |40->42, 264->exit, 373->exit |
| src/inspect\_flow/\_config/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/defaults.py             |       86 |        0 |       44 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/load.py                 |      259 |        3 |      104 |        2 |     98.62% |88, 97, 218 |
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
| src/inspect\_flow/\_runner/instantiate.py          |      158 |        1 |       74 |        2 |     98.71% |77, 243->245 |
| src/inspect\_flow/\_runner/logs.py                 |      116 |        1 |       52 |        4 |     97.02% |42, 169->167, 172->167, 201->196 |
| src/inspect\_flow/\_runner/resolve.py              |       13 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/run.py                  |      151 |        5 |       64 |        5 |     95.35% |165-166, 183, 185, 199, 233->232, 280->282 |
| src/inspect\_flow/\_runner/task\_log.py            |      136 |        0 |       48 |        0 |    100.00% |           |
| src/inspect\_flow/\_store/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_store/deltalake.py             |      336 |       16 |      114 |       14 |     93.33% |92->exit, 136, 153, 173->172, 179->172, 230-232, 260->266, 263->266, 340-341, 345, 384-386, 394, 396->399, 413, 544-545, 549 |
| src/inspect\_flow/\_store/store.py                 |       60 |        1 |       20 |        1 |     97.50% |102, 166->168 |
| src/inspect\_flow/\_types/\_\_init\_\_.py          |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/decorator.py             |        7 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/factories.py             |       83 |        0 |       32 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/flow\_types.py           |      172 |        3 |        8 |        0 |     96.11% |     67-69 |
| src/inspect\_flow/\_types/generated.py             |      249 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/log\_filter.py           |       36 |        4 |       18 |        3 |     87.04% |59, 71, 73-74 |
| src/inspect\_flow/\_types/merge.py                 |       27 |        0 |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/console.py                |       71 |        6 |       32 |        6 |     88.35% |28->exit, 40-43, 64->73, 89, 92, 106->108 |
| src/inspect\_flow/\_util/constants.py              |        3 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/data.py                   |       25 |        0 |        4 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/error.py                  |       32 |        2 |       10 |        1 |     92.86% |     32-35 |
| src/inspect\_flow/\_util/list\_util.py             |        8 |        0 |        2 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/logging.py                |       16 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/logs.py                   |       64 |       11 |       20 |        5 |     78.57% |23-30, 61, 76, 101, 107, 111->104 |
| src/inspect\_flow/\_util/module\_util.py           |       57 |        0 |       22 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/not\_given.py             |        9 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/path\_util.py             |       43 |        1 |       16 |        1 |     96.61% |        27 |
| src/inspect\_flow/\_util/pydantic\_util.py         |       19 |        0 |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/subprocess\_util.py       |       40 |       14 |       16 |        1 |     69.64% | 26-41, 98 |
| src/inspect\_flow/\_util/util.py                   |        3 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_version.py                     |       13 |        0 |        0 |        0 |    100.00% |           |
| src/inspect\_flow/api/\_\_init\_\_.py              |        6 |        0 |        0 |        0 |    100.00% |           |
| **TOTAL**                                          | **4010** |  **272** | **1218** |   **88** | **91.58%** |           |


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