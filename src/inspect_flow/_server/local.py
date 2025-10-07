from inspect_flow._config.config import load_config
from inspect_flow._runner import runner
from inspect_flow._server.api import ServerAPI


class LocalServer(ServerAPI):
    def get_config(self) -> None:
        pass

    def add_config(self, config_file: str) -> None:
        pass

    def submit(self, config_file: str) -> None:
        config = load_config(config_file)
        for task_group in config.run.task_groups:
            runner.run(task_group=task_group)
