from inspect_flow._server.local import LocalServer


class Client:
    server = LocalServer()

    def set_config(self, config_file: str) -> None:
        self.server.add_config(config_file)

    def submit(self) -> str:
        return self.server.submit()
