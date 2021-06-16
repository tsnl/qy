import abc
import enum
import dataclasses

from qcl import feedback
from qcl import type

from . import scheme


class BaseDef(object, metaclass=abc.ABCMeta):
    loc: feedback.ILoc
    scheme: scheme.Scheme
    universe: "DefinitionUniverse"

    def __init__(self, loc, new_scheme, universe):
        super().__init__()
        self.loc = loc
        self.scheme = new_scheme
        self.universe = universe


class ValueDef(BaseDef):
    def __init__(self, loc, value_tid):
        super().__init__(loc, scheme.Scheme(value_tid), DefinitionUniverse.Value)


class TypeDef(BaseDef):
    def __init__(self, loc, value_tid):
        super().__init__(loc, scheme.Scheme(value_tid), DefinitionUniverse.Type)


class ModDef(BaseDef):
    def __init__(self, loc, mod_scheme):
        super().__init__(loc, mod_scheme, DefinitionUniverse.Module)


# @dataclasses.dataclass
# class Definition(object):
#     loc: feedback.ILoc
#     universe: "DefinitionUniverse"
#     scheme: "scheme.Scheme"
#
#     def copy_with_new_scheme(self, new_scheme: "scheme.Scheme"):
#         """
#         :return: a copy of this definition object with the `scheme` field substituted.
#         """
#         return Definition(
#             loc=self.loc,
#             universe=self.universe,
#             scheme=new_scheme
#         )


@enum.unique
class DefinitionUniverse(enum.Enum):
    Type = enum.auto()
    Value = enum.auto()
    Module = enum.auto()

