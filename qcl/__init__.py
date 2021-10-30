import json

from . import config
from . import panic
from . import feedback as fb
from . import source


class Project(object):
    def __init__(self) -> None:
        super().__init__()

    def add_package(self, pkg: source.Qyp):
        pass
