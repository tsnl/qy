"""
This module verifies properties about values on a context-by-context/scope-by-scope basis.

TODO: check that `TOT`-assignment not misused, i.e.
    - then, try to eliminate `TOT` specifier syntax for assign expression-- can just be inferred.
    - check that pointer contents can never be non-local
    - rather than SMT analysis, consider logical CFA
"""

import abc
import typing as t

from qcl import type
from qcl import excepts
from qcl import frontend
from qcl import feedback as fb
from qcl import ast


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
    def __init__(self, loc: fb.ILoc, type_of_tid: type.identity.TID):
        super().__init__()
        self.loc = loc
        self.type_of_tid = type_of_tid

    def assign_from(self, src_value_model: "BaseValueModel", for_fn_call: bool = False):
        if isinstance(src_value_model, self.__class__):
            self.assign_from_impl(src_value_model, for_fn_call)
        else:
            raise excepts.CompilerError("Assignment of incorrect type, but passes type-check.")

    @abc.abstractmethod
    def assign_from_impl(self, src_value_model: "BaseValueModel", for_fn_call: bool):
        pass


class UnitValueModel(BaseValueModel):
    def assign_from_impl(self, src_value_model: "BaseValueModel", for_fn_call: bool):
        pass


class StringValueModel(BaseValueModel):
    def assign_from_impl(self, src_value_model: "BaseValueModel", for_fn_call: bool):
        pass


#
# Memory Window types:
#

class BaseMemWindowValueModel(BaseValueModel):
    """
    all mem-window values treat all pointed data elements as one--
    no more granular than that is feasible.
    """

    def __init__(
            self,
            loc: fb.ILoc,
            type_of_tid: type.identity.TID,
            init_content_val_model: "BaseValueModel",
            init_content_lifetime: type.lifetime.LifetimeID,
            contents_may_be_local: bool,
            contents_may_be_non_local: bool
    ):
        assert self.__class__ is not BaseMemWindowValueModel
        super().__init__(loc, type_of_tid)
        self.content_val_model = init_content_val_model
        self.content_lifetime_set = {
            init_content_lifetime
        }
        self.contents_may_be_frame_local = contents_may_be_local

    def store_from(self, stored_value_model: "BaseValueModel"):
        if isinstance(stored_value_model, self.__class__):
            self.store_from_impl(stored_value_model)
        else:
            raise excepts.CompilerError("Store of incorrect type, but passes type-check.")

    def store_from_impl(self, stored_value_model: "BaseValueModel"):
        # assigning to the content model:
        self.content_val_model.assign_from(stored_value_model, for_fn_call=False)

    def assign_from_impl(self, src_mw_value_model: "BaseValueModel", for_fn_call: bool):
        assert isinstance(src_mw_value_model, BaseMemWindowValueModel)
        self.content_val_model.assign_from(src_mw_value_model.content_val_model, for_fn_call)
        self.content_lifetime_set |= src_mw_value_model.content_lifetime_set

        if not for_fn_call:
            self.contents_may_be_frame_local |= src_mw_value_model.contents_may_be_frame_local


class PointerValueModel(BaseMemWindowValueModel):
    pass


class ArrayValueModel(BaseMemWindowValueModel):
    pass


class SliceValueModel(BaseMemWindowValueModel):
    pass


#
# Function models:
#

class FuncValueModel(BaseValueModel):
    def assign_from_impl(self, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for FuncValueModel")


#
# Tuple/Struct models:
#

class TupleValueModel(BaseValueModel):
    def assign_from_impl(self, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for TupleValueModel")


class StructValueModel(BaseValueModel):
    def assign_from_impl(self, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for StructValueModel")


#
# Union models:
#

class UnionValueModel(BaseValueModel):
    def assign_from_impl(self, src_value_model: "BaseValueModel", for_fn_call: bool):
        raise NotImplementedError("`assign_from` for UnionValueModel")


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
        for file_mod_exp in project.file_module_exp_list:
            self.check_file_mod_exp(file_mod_exp)

    def check_file_mod_exp(self, file_mod_exp: "ast.node.FileModExp"):
        raise NotImplementedError("Analyzer.check_file_mod_exp")

    def check_sub_mod_exp(self, sub_mod_name: str, sub_mod_exp: "ast.node.SubModExp"):
        raise NotImplementedError("Analyzer.check_sub_mod_exp")

    def check_exp(self, exp: "ast.node.BaseExp"):
        raise NotImplementedError("Analyzer.check_exp")

    def check_type_spec(self, ts: "ast.node.BaseTypeSpec"):
        raise NotImplementedError("Analyzer.check_type_spec")
