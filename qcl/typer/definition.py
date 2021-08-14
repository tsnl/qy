import abc
import enum
import typing as t

from qcl import feedback
from qcl import type
from qcl import ast
from qcl import frontend

from . import scheme


class BaseRecord(object, metaclass=abc.ABCMeta):
    def __init__(
            self,
            project: "frontend.Project",
            name: str, loc: "feedback.ILoc",
            new_scheme: "scheme.Scheme", universe: "Universe",
            opt_func: t.Optional["ast.node.LambdaExp"],
            is_protected_from_global_scope: bool
    ):
        assert isinstance(new_scheme, scheme.Scheme)
        super().__init__()
        self.project: "frontend.Project" = project
        self.name: str = name
        self.loc: feedback.ILoc = loc
        self.scheme: scheme.Scheme = new_scheme
        self.universe: "Universe" = universe
        self.opt_container_func: t.Optional["ast.node.LambdaExp"] = opt_func
        self.is_protected_from_global_scope: bool = is_protected_from_global_scope
        self.opt_container_submodule: t.Optional["ast.node.SubModExp"] = None

    @property
    def is_globally_visible(self):
        return self.opt_container_func is None and not self.is_protected_from_global_scope

    def init_def_context(self, def_context):
        # storing the container sub-module:
        self.opt_container_submodule = def_context.opt_container_submodule

        # initializing the scheme:
        self.scheme.init_def_context(def_context)


class ValueRecord(BaseRecord):
    def __init__(
            self,
            project: "frontend.Project",
            name: str,
            loc: feedback.ILoc,
            value_tid: type.identity.TID,
            opt_func,
            is_protected_from_global_scope=True
    ):
        super().__init__(
            project,
            name, loc,
            scheme.Scheme(value_tid), Universe.Value,
            opt_func, is_protected_from_global_scope
        )

        if self.is_globally_visible:
            all_global_value_recs.append(self)

        self.val_def_id = self.project.allocate_val_def_id(self)


class TypeRecord(BaseRecord):
    def __init__(
            self,
            project: "frontend.Project",
            name: str, loc: feedback.ILoc, type_tid: type.identity.TID,
            opt_func,
            is_protected_from_global_scope=True
    ):
        super().__init__(
            project,
            name, loc,
            scheme.Scheme(type_tid),
            Universe.Type,
            opt_func,
            is_protected_from_global_scope
        )

        if self.is_globally_visible:
            all_global_type_recs.append(self)


class ModRecord(BaseRecord):
    def __init__(self, project: "frontend.Project", name: str, loc: feedback.ILoc, mod_scheme: scheme.Scheme, mod_exp: "ast.node.BaseModExp"):
        super().__init__(
            project,
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
