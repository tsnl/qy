import abc

from . import ast2


class BaseEmitter(abc.ABC):
    def __init__(self) -> None:
        super().__init__()

    @abc.abstractmethod
    def emit_qyp_set(self, qyp_set: ast2.QypSet):
        pass
