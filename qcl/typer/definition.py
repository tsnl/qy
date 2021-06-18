import abc
import enum

from qcl import feedback
from qcl import type
from qcl import ast

from . import scheme


class BaseRecord(object, metaclass=abc.ABCMeta):
    loc: feedback.ILoc
    scheme: scheme.Scheme
    universe: "Universe"

    def __init__(self, loc: "feedback.ILoc", new_scheme: "scheme.Scheme", universe: "Universe"):
        assert isinstance(new_scheme, scheme.Scheme)
        super().__init__()
        self.loc = loc
        self.scheme = new_scheme
        self.universe = universe


class ValueRecord(BaseRecord):
    def __init__(self, loc: feedback.ILoc, value_tid: type.identity.TID):
        super().__init__(loc, scheme.Scheme(value_tid), Universe.Value)


class TypeRecord(BaseRecord):
    def __init__(self, loc: feedback.ILoc, type_tid: type.identity.TID):
        super().__init__(loc, scheme.Scheme(type_tid), Universe.Type)


class ModRecord(BaseRecord):
    def __init__(self, loc: feedback.ILoc, mod_scheme: scheme.Scheme, mod_exp: ast.node.BaseModExp):
        super().__init__(loc, mod_scheme, Universe.Module)
        self.mod_exp = mod_exp


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
class Universe(enum.Enum):
    Type = enum.auto()
    Value = enum.auto()
    Module = enum.auto()
