from inspect_flow._server.api import ServerAPI


class LocalServer(ServerAPI):
    def get_config(self) -> None:
        pass

    def add_config(self, config_file: str) -> None:
        pass

    def submit(self) -> str:
        return "job-id"
