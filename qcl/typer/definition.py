import abc
import enum

from qcl import feedback
from qcl import type
from qcl import ast

from . import scheme


class BaseRecord(object, metaclass=abc.ABCMeta):
    name: str
    loc: feedback.ILoc
    scheme: scheme.Scheme
    universe: "Universe"
    is_globally_visible: bool

    def __init__(self, name: str, loc: "feedback.ILoc", new_scheme: "scheme.Scheme", universe: "Universe", is_globally_visible: bool):
        assert isinstance(new_scheme, scheme.Scheme)
        super().__init__()
        self.name = name
        self.loc = loc
        self.scheme = new_scheme
        self.universe = universe
        self.is_globally_visible = is_globally_visible


class ValueRecord(BaseRecord):
    def __init__(self, name: str, loc: feedback.ILoc, value_tid: type.identity.TID, is_globally_visible: bool):
        super().__init__(name, loc, scheme.Scheme(value_tid), Universe.Value, is_globally_visible)
        
        if is_globally_visible:
            all_global_value_recs.append(self)


class TypeRecord(BaseRecord):
    def __init__(self, name: str, loc: feedback.ILoc, type_tid: type.identity.TID, is_globally_visible: bool):
        super().__init__(name, loc, scheme.Scheme(type_tid), Universe.Type, is_globally_visible)

        if is_globally_visible:
            all_global_type_recs.append(self)


class ModRecord(BaseRecord):
    def __init__(self, name: str, loc: feedback.ILoc, mod_scheme: scheme.Scheme, mod_exp: "ast.node.BaseModExp"):
        super().__init__(name, loc, mod_scheme, Universe.Module, is_globally_visible=True)
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



#
# For subsequent analysis, we store filtered lists of different definition records.
# These lists are assembled DURING CTOR CALLS and are used by POST-TYPECHECK-CHECKS
# FIXME: migrate these lists to within the 'Project' instance.
#

all_global_value_recs = []
all_global_type_recs = []