from abc import ABC, abstractmethod


class ServerAPI(ABC):
    @abstractmethod
    def get_config(self) -> None:
        pass
