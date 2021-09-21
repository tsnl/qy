import abc
import enum
import typing as t

from qcl import feedback
from qcl import types
from qcl import ast
from qcl import frontend

from . import scheme


class BaseRecord(object, metaclass=abc.ABCMeta):
    def __init__(
            self,
            project: "frontend.Project",
            name: str, loc: "feedback.ILoc",
            new_scheme: "scheme.Scheme",
            universe: "Universe",
            opt_func: t.Optional["ast.node.LambdaExp"],
            is_bound_globally_visible: bool,
            def_is_bound_var: bool
    ):
        assert isinstance(new_scheme, scheme.Scheme)
        super().__init__()
        self.project: "frontend.Project" = project
        self.name: str = name
        self.loc: feedback.ILoc = loc
        self.scheme: scheme.Scheme = new_scheme
        self.universe: "Universe" = universe
        self.opt_container_func: t.Optional["ast.node.LambdaExp"] = opt_func
        self.opt_container_submodule: t.Optional["ast.node.SubModExp"] = None
        self.is_bound_globally_visible = is_bound_globally_visible
        self.is_bound_var_def_obj = def_is_bound_var

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
            value_tid: types.identity.TID,
            opt_func,
            is_bound_globally_visible: bool,
            def_is_bound_var: bool
    ):
        super().__init__(
            project,
            name, loc,
            scheme.Scheme(value_tid), Universe.Value,
            opt_func,
            is_bound_globally_visible=is_bound_globally_visible,
            def_is_bound_var=def_is_bound_var
        )

        self.val_def_id = self.project.allocate_val_def_id(self)


class TypeRecord(BaseRecord):
    def __init__(
            self,
            project: "frontend.Project",
            name: str, loc: feedback.ILoc, type_tid: types.identity.TID,
            opt_func,
            is_bound_globally_visible,
            def_is_bound_var
    ):
        super().__init__(
            project,
            name, loc,
            scheme.Scheme(type_tid),
            Universe.Type,
            opt_func=opt_func,
            is_bound_globally_visible=is_bound_globally_visible,
            def_is_bound_var=def_is_bound_var
        )


class ModRecord(BaseRecord):
    def __init__(
            self,
            project: "frontend.Project",
            name: str, loc: feedback.ILoc,
            mod_scheme: scheme.Scheme, mod_exp: "ast.node.BaseModExp"
    ):
        super().__init__(
            project,
            name, loc,
            mod_scheme, Universe.Module,
            opt_func=None,
            is_bound_globally_visible=True,     # all modules are globally visible
            def_is_bound_var=False              # no module can be used as a template arg
        )
        self.mod_exp = mod_exp

        # map 1-1 DefRec to Mod:
        assert self.mod_exp.own_def_rec_from_typer is None
        self.mod_exp.own_def_rec_from_typer = self


@enum.unique
class Universe(enum.Enum):
    Type = enum.auto()
    Value = enum.auto()
    Module = enum.auto()
