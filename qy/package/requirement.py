import abc
import typing as ts

from .version_constraint import VersionConstraint


class Requirement(abc.ABC):
    def __init__(self, provider: str, version_constraints: ts.List["VersionConstraint"]) -> None:
        super().__init__()
        self.provider: str = provider
        self.version_constraints = version_constraints


class GitRequirement(Requirement):
    def __init__(self, location: str, version_constraints: ts.List["VersionConstraint"]):
        super().__init__("git", version_constraints)
        self.location = location


class FilesystemRequirement(Requirement):
    def __init__(self, location: str, version_constraints: ts.List["VersionConstraint"]):
        super().__init__("filesystem", version_constraints)
        self.location = location
