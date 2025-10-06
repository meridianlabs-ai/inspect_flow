import json

from inspect_flow._types.types import TaskGroupConfig


def read_config() -> TaskGroupConfig:
    with open("task_group.json", "r") as f:
        data = json.load(f)
        return TaskGroupConfig(**data)


def main() -> None:
    config = read_config()
    print(config)
    pass


if __name__ == "__main__":
    main()
