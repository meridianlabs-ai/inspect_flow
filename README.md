# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/meridianlabs-ai/inspect_flow/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                               |    Stmts |     Miss |      Cover |   Missing |
|--------------------------------------------------- | -------: | -------: | ---------: | --------: |
| src/inspect\_flow/\_\_init\_\_.py                  |        7 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/\_\_init\_\_.py            |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_api/api.py                     |       22 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/\_\_init\_\_.py            |        3 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/config.py                  |       18 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/main.py                    |       19 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/options.py                 |       35 |        0 |    100.00% |           |
| src/inspect\_flow/\_cli/run.py                     |       19 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/\_\_init\_\_.py         |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/defaults.py             |       68 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/load.py                 |      221 |        0 |    100.00% |           |
| src/inspect\_flow/\_config/write.py                |        5 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/\_\_init\_\_.py       |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/auto\_dependencies.py |       66 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/launch.py             |       60 |        0 |    100.00% |           |
| src/inspect\_flow/\_launcher/pip\_string.py        |       75 |       26 |     65.33% |20-24, 87-88, 95-105, 115-132 |
| src/inspect\_flow/\_launcher/venv.py               |       99 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/\_\_init\_\_.py         |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/instantiate.py          |      103 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/resolve.py              |       50 |        0 |    100.00% |           |
| src/inspect\_flow/\_runner/run.py                  |       72 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/\_\_init\_\_.py          |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/decorator.py             |        5 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/factories.py             |       61 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/flow\_types.py           |      133 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/generated.py             |      162 |        0 |    100.00% |           |
| src/inspect\_flow/\_types/merge.py                 |       27 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/\_\_init\_\_.py           |        0 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/args.py                   |        1 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/constants.py              |        3 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/error.py                  |       16 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/list\_util.py             |        6 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/logging.py                |        8 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/module\_util.py           |       56 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/not\_given.py             |        9 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/path\_util.py             |       16 |        0 |    100.00% |           |
| src/inspect\_flow/\_util/subprocess\_util.py       |       18 |        0 |    100.00% |           |
| src/inspect\_flow/\_version.py                     |       13 |        0 |    100.00% |           |
| src/inspect\_flow/api/\_\_init\_\_.py              |        2 |        0 |    100.00% |           |
| **TOTAL**                                          | **1478** |   **26** | **98.24%** |           |


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