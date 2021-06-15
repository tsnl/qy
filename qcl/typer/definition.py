import enum
import dataclasses

from qcl import feedback
from qcl import scheme


@dataclasses.dataclass
class Definition(object):
    loc: feedback.ILoc
    universe: "DefinitionUniverse"
    scheme: "scheme.Scheme"

    def copy_with_new_scheme(self, new_scheme: "scheme.Scheme"):
        """
        :return: a copy of this definition object with the `scheme` field substituted.
        """
        return Definition(
            loc=self.loc,
            universe=self.universe,
            scheme=new_scheme
        )


@enum.unique
class DefinitionUniverse(enum.Enum):
    Type = enum.auto()
    Value = enum.auto()
