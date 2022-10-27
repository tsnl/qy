import abc

from .version import Version


class VersionConstraint(abc.ABC):
    def __init__(self, version_point: "Version"):
        super().__init__()
        self.point = version_point


class ExactVersionConstraint(VersionConstraint):
    def __eq__(self, o: object) -> bool:
        return isinstance(o, ExactVersionConstraint) and self.point == o.point


@abc.abstractmethod
class RelVersionConstraint(VersionConstraint):
    def __init__(self, version_point: "Version", closed_endpoint: bool):
        super().__init__(version_point)
        self.closed = closed_endpoint

    @staticmethod
    @abc.abstractmethod
    def ordering_string():
        pass

    def __str__(self) -> str:
        return (
            self.ordering_string() +
            ("" if not self.closed else "=") +
            str(self.point)
        )

    def __eq__(self, o: object) -> bool:
        return (
            isinstance(o, self.__class__) and 
            self.point == o.point and
            self.closed == o.closed
        )


class MinVersionConstraint(RelVersionConstraint):
    def ordering_string():
        return ">"
    

class MaxVersionConstraint(RelVersionConstraint):
    def ordering_string():
        return "<"
