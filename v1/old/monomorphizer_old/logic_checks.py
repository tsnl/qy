"""
This module verifies properties about values on a context-by-context/scope-by-scope basis.

TODO: check that `TOT`-assignment not misused, i.e.
    - then, try to eliminate `TOT` specifier syntax for assign expression-- can just be inferred.
    - check that pointer contents can never be non-local
    - rather than SMT analysis, consider logical CFA

TODO: run this AFTER monomorphization
"""

import abc
import enum
import typing as t
import functools

from qcl import types
from qcl import excepts
from qcl import frontend
from qcl import feedback as fb
from qcl import ast
from qcl import typer


#
# Entry point:
#

def run(project):
    a = Analyzer()
    a.check_project(project)


#
#
# Value models:
#
#


#
# Simplest types:
#

class BaseValueModel(object, metaclass=abc.ABCMeta):
    def __init__(self, loc: fb.ILoc, type_of_tid: types.identity.TID):
        super().__init__()
        self.loc = loc
        self.type_of_tid = type_of_tid

    def assign_from(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool = False) -> "BaseValueModel":
        if isinstance(src_value_model, self.__class__):
            return self.assign_from_impl(loc, src_value_model, for_fn_call)
        else:
            raise excepts.CompilerError("Assignment of incorrect types, but passes types-check.")

    @abc.abstractmethod
    def assign_from_impl(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool) -> "BaseValueModel":
        pass

    @classmethod
    def unify(cls, loc: "fb.ILoc", *vs) -> "BaseValueModel":
        """
        This function is used to replace multiple possible value models across branches with one value model with
        properties abstracted for all of the branches.
        In branch-less code, a ValueModel is as precise as possible, allowing us to make deterministic judgements about
        code's state.
        Properties are 'unified' by finding the 'or' of each input
        :param loc: the location of the node whose value is modeled by the union value model
        :param vs: a sequence of BaseValueModel subclass instances
        :return: a ValueModel that unifies (replaces) all `vs`
        """

        assert all((lambda v: isinstance(v, cls) for v in vs))
        return functools.reduce(
            lambda a, b: cls.unify_impl(loc, a, b),
            vs
        )

    @classmethod
    @abc.abstractmethod
    def unify_impl(
            cls,
            loc: "fb.ILoc",
            v1: "BaseValueModel",
            v2: "BaseValueModel"
    ) -> "BaseValueModel":
        pass


class UnitValueModel(BaseValueModel):
    def __init__(
            self,
            loc: "fb.ILoc"
    ):
        super().__init__(loc, types.get_unit_type())

    def assign_from_impl(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool) -> "UnitValueModel":
        return UnitValueModel(loc)

    @classmethod
    def unify_impl(cls, loc, v1, v2) -> "BaseValueModel":
        return UnitValueModel(loc)


class StringValueModel(BaseValueModel):
    def __init__(
            self,
            loc: "fb.ILoc",
            value_set: t.Set[str]
    ):
        super().__init__(loc, types.get_str_type())
        self.value_set = value_set

    def assign_from_impl(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool):
        assert isinstance(src_value_model, StringValueModel)
        return StringValueModel(
            loc,
            src_value_model.value_set
        )

    @classmethod
    def unify_impl(cls, loc, v1, v2):
        assert isinstance(v1, StringValueModel)
        assert isinstance(v2, StringValueModel)
        return StringValueModel(
            loc,
            v1.value_set | v2.value_set
        )


#
# Memory Window types:
#

class MemWindowKind(enum.Enum):
    Pointer = enum.auto()
    Array = enum.auto()
    Slice = enum.auto()


class MemWindowValueModel(BaseValueModel):
    """
    all mem-window values treat all pointed data elements as one--
    no more granular than that is feasible.
    """

    def __init__(
            self,
            loc: fb.ILoc,
            type_of_tid: types.identity.TID,
            content_val_model: "BaseValueModel",
            content_lifetime_set: t.Set[types.lifetime.LifetimeID],
            contents_may_be_frame_local: bool,
            contents_may_be_frame_non_local: bool = False,
    ):
        super().__init__(loc, type_of_tid)
        self.content_val_model = content_val_model
        self.content_lifetime_set = content_lifetime_set
        self.contents_may_be_frame_local = contents_may_be_frame_local
        self.contents_may_be_frame_non_local = contents_may_be_frame_non_local
        self.window_kind = {
            types.kind.TK.Pointer: MemWindowKind.Pointer,
            types.kind.TK.Array: MemWindowKind.Array,
            types.kind.TK.Slice: MemWindowKind.Slice
        }[types.kind.of(type_of_tid)]

    def store_from(self, loc, stored_value_model: "BaseValueModel"):
        if isinstance(stored_value_model, self.__class__):
            return self.store_from_impl(loc, stored_value_model)
        else:
            raise excepts.CompilerError("Store of incorrect types, but passes types-check.")

    def store_from_impl(self, loc, stored_value_model: "BaseValueModel"):
        # assigning to the content model:
        stored_val_model = self.content_val_model.assign_from(stored_value_model, for_fn_call=False)
        self.content_val_model = BaseValueModel.unify(loc, self.content_val_model, stored_val_model)

    def assign_from_impl(self, loc, src_mw_value_model: "BaseValueModel", for_fn_call: bool):
        assert isinstance(src_mw_value_model, MemWindowValueModel)
        assert self.type_of_tid == src_mw_value_model.type_of_tid

        return MemWindowValueModel(
            loc,
            src_mw_value_model.type_of_tid,
            src_mw_value_model.content_val_model,
            src_mw_value_model.content_lifetime_set,
            contents_may_be_frame_local=(
                False
                if for_fn_call else
                src_mw_value_model.contents_may_be_frame_local
            ),
            contents_may_be_frame_non_local=(
                True
                if for_fn_call else
                src_mw_value_model.contents_may_be_frame_non_local
            )
        )

    @classmethod
    def unify_impl(
            cls,
            loc: "fb.ILoc",
            v1: "BaseValueModel",
            v2: "BaseValueModel"
    ) -> "BaseValueModel":
        assert isinstance(v1, MemWindowValueModel)
        assert isinstance(v2, MemWindowValueModel)
        assert v1.type_of_tid == v2.type_of_tid

        type_of_tid = v1.type_of_tid
        return MemWindowValueModel(
            loc,
            type_of_tid,
            content_val_model=BaseValueModel.unify(
                loc,
                v1.content_val_model,
                v2.content_val_model
            ),
            content_lifetime_set=(v1.content_lifetime_set | v2.content_lifetime_set),
            contents_may_be_frame_local=(v1.contents_may_be_frame_local or v2.contents_may_be_frame_local),
            contents_may_be_frame_non_local=(v1.contents_may_be_frame_non_local or v2.contents_may_be_frame_non_local)
        )


#
# Function models:
#

class FuncValueModel(BaseValueModel):
    # use field value args to track...
    #   - formal arg
    #   - actual arg
    #   - return arg

    def assign_from_impl(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for FuncValueModel")

    @classmethod
    def unify_impl(
            cls,
            loc: "fb.ILoc",
            v1: "BaseValueModel",
            v2: "BaseValueModel"
    ) -> "BaseValueModel":
        raise NotImplementedError("`unify` for FuncValueModel")


#
# Tuple/Struct models:
#

class TupleValueModel(BaseValueModel):
    def assign_from_impl(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for TupleValueModel")

    @classmethod
    def unify_impl(
            cls,
            loc: "fb.ILoc",
            v1: "BaseValueModel",
            v2: "BaseValueModel"
    ) -> "BaseValueModel":
        raise NotImplementedError("`unify` for TupleValueModel")


class StructValueModel(BaseValueModel):
    def assign_from_impl(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for StructValueModel")

    @classmethod
    def unify_impl(
            cls,
            loc: "fb.ILoc",
            v1: "BaseValueModel",
            v2: "BaseValueModel"
    ) -> "BaseValueModel":
        raise NotImplementedError("`unify` for TupleValueModel")


#
# Union models:
#

class UnionValueModel(BaseValueModel):
    def assign_from_impl(self, loc, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for UnionValueModel")

    @classmethod
    def unify_impl(
            cls,
            loc: "fb.ILoc",
            v1: "BaseValueModel",
            v2: "BaseValueModel"
    ) -> "BaseValueModel":
        raise NotImplementedError("`unify` for UnionValueModel")


#
#
# Analysis Context:
#   TODO: instantiate a `ValueModel` for each variable
#       - convert/lower code to use variables for everything, similar to SSA
#           - recursion with return just does this
#       - allow assignment to and from value models
#       - check for the weakest post-condition/pre-condition that holds for each statement
#
#

class Analyzer(object):
    def __init__(self):
        self.symbol_table: t.Dict[int, BaseValueModel] = {}

    def define(self, def_id: int, initial_value_model: "BaseValueModel"):
        assert def_id not in self.symbol_table
        self.symbol_table[def_id] = initial_value_model

    def lookup(self, def_id: int) -> "BaseValueModel":
        return self.symbol_table[def_id]

    def check_project(self, project: "frontend.Project"):
        # defining all value definitions in the entire project using a non-scoped, def-unique ID:
        for def_val_rec in project.all_def_val_rec_list:
            assert isinstance(def_val_rec, typer.definition.ValueRecord)
            val_model = self.instantiate_default_val_model_for_def(def_val_rec)
            self.define(
                def_val_rec.val_def_id,
                val_model
            )

        for file_mod_exp in project.file_module_exp_list:
            self.check_file_mod_exp(file_mod_exp)

    def check_file_mod_exp(self, file_mod_exp: "ast.node.FileModExp"):
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            self.check_sub_mod_exp(sub_mod_name, sub_mod_exp)

    def check_sub_mod_exp(self, sub_mod_name: str, sub_mod_exp: "ast.node.SubModExp"):
        for elem in sub_mod_exp.table.ordered_value_imp_bind_elems:
            self.check_global_bind_elem(elem)

    def check_global_bind_elem(
            self,
            elem: "ast.node.Bind1VElem"
    ):
        assert isinstance(elem, ast.node.Bind1VElem)
        self.check_exp(elem.bound_exp)

    def check_exp(self, exp: "ast.node.BaseExp"):
        raise NotImplementedError("Analyzer.check_exp")

    def instantiate_default_val_model_for_def(self, def_val_rec: "typer.definition.ValueRecord"):
        def_tid = def_val_rec.val_def_id

        # TODO: what about polymorphic arguments?
        #   CANT instantiate formal types arg `T` unless we have all instantiations
        #   THUS, we need to run this pass AFTER monomorphization
        #   THUS, we must ignore or dynamically check for violations of `TOT` assignment
        #   - can be performed within `vm` module

        raise NotImplementedError("Instantiating a default ValueModel based on TID")
