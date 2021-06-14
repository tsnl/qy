import enum
import dataclasses

from qcl import feedback


@dataclasses.dataclass
class Definition(object):
    loc: feedback.ILoc
    universe: "DefinitionUniverse"
    scheme: "scheme.Scheme"


@enum.unique
class DefinitionUniverse(enum.Enum):
    Type = enum.auto()
    Value = enum.auto()
