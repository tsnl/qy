import abc
from dataclasses import dataclass
import typing as ts

from .version import Version
from .requirement import Requirement


@dataclass
class Package:
    author: str
    version: "Version"
    description: str
    requirements: ts.List["Requirement"]
