import abc

from .version import Version


class VersionConstraint(abc.ABC):
    def __init__(self, version_point: "Version"):
        super().__init__()
        self.point = version_point


class MinVersionConstraint(VersionConstraint):
    def __init__(self, version_point: "Version", closed_endpoint: bool):
        super().__init__(version_point)
        self.closed = closed_endpoint


class MaxVersionConstraint(VersionConstraint):
    def __init__(self, version_point: "Version", closed_endpoint: bool):
        super().__init__(version_point)
        self.closed = closed_endpoint


class ExactVersionConstraint(VersionConstraint):
    pass
