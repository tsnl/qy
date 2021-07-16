"""
SVA = Symbolic Value Analysis
This module allows us to perform inferences on the results of expressions in tandem with type analysis.
We create a symbolic representation of program execution within which certain properties can be lazily evaluated using
induction.
It is used to perform CFA-related checks like...
 - track where pointers may be allocated
 - (possible) check integer bounds for overflow errors
OVERVIEW:
- Each algebraic value is represented by a variable, i.e. a `ValVar` instance.
    - stable wrapper around changing inferences
- Each variable may accept several incoming edges indicating the potential flow of values from one variable into another
    - the source of flow is specified as a variable which can be passed around, annotated, and reused
- Each value definition has a unique ValVar associated with it.
- When values must be inferred by type inference, they can be left un-initialized and un-typed
- When `ValVar` are instantiated in different contexts, they have different inference properties
    - e.g. `content_may_be_local`
The `ValVar` instance acts as a proxy for a duck-typed value of any type that relies on symbolic computation.
USAGE:
- First, initialize constraints using `ValVar` instances
    - create a `ValVar` for each value
    - use `relate_?`
"""

import abc
import typing as t

from qcl import type
from qcl import feedback as fb


class ValVar(object):
    def __init__(self, client_name: str, client_loc: fb.ILoc, opt_initial_value=None):
        super().__init__()
        self.client_name = client_name
        self.client_loc = client_loc
        self.opt_value = opt_initial_value
        self.flow_src_list = []

    def add_incoming(self, val_var: "ValVar"):
        self.flow_src_list.append(val_var)

    def get_value(self):
        if self.opt_value is not None:
            return self.opt_value
        else:
            raise NotImplementedError("reducing `flow_src_list` into a value, raising excepts if failed")

    # TODO: write `relate_?` functions to support different value kinds:
    #   - e.g. for func: 'get arg val var', 'get ret val var'
    #   - e.g. for struct: 'get field val var'
    #   - if we have an `opt_value`, we can look it up directly.
    #   - otherwise, we must add a constraint to a deferred set that is resolved when `get_value` is called.
    #   - BETTER: store constraints, map to ALL values in `flow_src_list` (OR depending on edge rules)


class BaseValue(object, metaclass=abc.ABCMeta):
    pass


class UnitValue(BaseValue):
    pass


class IntValue(BaseValue):
    def __init__(self):
        super().__init__()


class FloatValue(BaseValue):
    def __init__(self):
        super().__init__()


class StringValue(BaseValue):
    pass


class MemWindowValue(BaseValue):
    content_mem_loc_set: t.Set[type.mem_loc.MemLocID]
    content_mem_may_be_local: bool
    content_mem_may_be_non_local: bool
    ptd_value_info: ValVar

    def __init__(self, content_mem_may_be_local, content_mem_may_be_non_local, ptd_value_info: ValVar):
        super().__init__()
        self.content_mem_loc_set = set()
        self.content_mem_may_be_local = content_mem_may_be_local
        self.content_mem_may_be_non_local = content_mem_may_be_non_local
        self.ptd_value_info = ptd_value_info


class BaseCompound(BaseValue):
    def __init__(self, elem_value_info_list: t.List[ValVar]):
        super().__init__()
        self.elem_value_info_list = elem_value_info_list


class FuncValue(BaseCompound):
    def __init__(self, arg_val_var: ValVar, ret_val_var: ValVar):
        super().__init__([arg_val_var, ret_val_var])

    @property
    def arg_val_var(self):
        return self.elem_value_info_list[0]

    @property
    def ret_val_var(self):
        return self.elem_value_info_list[1]


class TupleValue(BaseCompound):
    def __init__(self, elem_value_info_list: t.List[ValVar]):
        super().__init__(elem_value_info_list)


class StructValue(BaseCompound):
    def __init__(self, elem_value_info_list: t.List[ValVar]):
        super().__init__(elem_value_info_list)


class UnionValue(BaseValue):
    def __init__(self, stored_value_info: ValVar):
        super().__init__()
        self.stored_value_info = stored_value_info
