import abc
import enum
import typing as t

from qcl import feedback
from qcl import type
from qcl import ast

from . import scheme


class BaseRecord(object, metaclass=abc.ABCMeta):
    name: str
    loc: feedback.ILoc
    scheme: scheme.Scheme
    universe: "Universe"
    opt_container_func: t.Optional["ast.node.LambdaExp"]

    def __init__(
            self,
            name: str, loc: "feedback.ILoc",
            new_scheme: "scheme.Scheme", universe: "Universe",
            opt_func: t.Optional["ast.node.LambdaExp"],
            is_protected_from_global_scope: bool
    ):
        assert isinstance(new_scheme, scheme.Scheme)
        super().__init__()
        self.name = name
        self.loc = loc
        self.scheme = new_scheme
        self.universe = universe
        self.opt_container_func = opt_func
        self.is_protected_from_global_scope = is_protected_from_global_scope

    @property
    def is_globally_visible(self):
        return self.opt_container_func is None and not self.is_protected_from_global_scope


class ValueRecord(BaseRecord):
    def __init__(
            self,
            name: str, loc: feedback.ILoc, value_tid: type.identity.TID,
            opt_func,
            is_protected_from_global_scope=True
    ):
        super().__init__(
            name, loc,
            scheme.Scheme(value_tid), Universe.Value,
            opt_func, is_protected_from_global_scope
        )

        if self.is_globally_visible:
            all_global_value_recs.append(self)


class TypeRecord(BaseRecord):
    def __init__(
            self,
            name: str, loc: feedback.ILoc, type_tid: type.identity.TID,
            opt_func,
            is_protected_from_global_scope=True
    ):
        super().__init__(name, loc, scheme.Scheme(type_tid), Universe.Type, opt_func, is_protected_from_global_scope)

        if self.is_globally_visible:
            all_global_type_recs.append(self)


class ModRecord(BaseRecord):
    def __init__(self, name: str, loc: feedback.ILoc, mod_scheme: scheme.Scheme, mod_exp: "ast.node.BaseModExp"):
        super().__init__(
            name, loc,
            mod_scheme, Universe.Module,
            opt_func=None,
            is_protected_from_global_scope=False
        )
        self.mod_exp = mod_exp


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
