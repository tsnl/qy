"""
Each type is just a unique integer ID.
Each sub-module of this package manages a system, or a co-located facet some type.
We guarantee a structural type system using `functools.cache` + a nominal wrapper to create type.
"""

import functools

from typing import *

from . import identity
from . import kind
from . import elem
from . import scalar_width_in_bytes
from . import is_mut
from . import spelling
from . import side_effects
from . import free


@functools.cache
def get_unit_type():
    tid = identity.mint()
    kind.init(tid, kind.TK.Unit)
    return tid


@functools.cache
def get_int_type(width_in_bytes: int, is_unsigned=False) -> identity.TID:
    tid = identity.mint()
    if is_unsigned:
        kind.init(tid, kind.TK.UnsignedInt)
    else:
        kind.init(tid, kind.TK.SignedInt)
    scalar_width_in_bytes.init(tid, width_in_bytes)
    return tid


@functools.cache
def get_float_type(width_in_bytes: int) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Float)
    scalar_width_in_bytes.init(tid, width_in_bytes)
    return tid


@functools.cache
def get_str_type() -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.String)
    return tid


@functools.cache
def get_ptr_type(ptd_tid: identity.TID, ptr_is_mut: bool) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Pointer)
    elem.init_ptr(tid, ptd_tid)
    is_mut.init_ptr(tid, ptr_is_mut)
    return tid


@functools.cache
def get_array_type(ptd_tid: identity.TID, array_is_mut: bool) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Array)
    elem.init_array(tid, ptd_tid)
    is_mut.init_array(tid, array_is_mut)
    return tid


@functools.cache
def get_slice_type(ptd_tid: identity.TID, slice_is_mut: bool) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Slice)
    elem.init_slice(tid, ptd_tid)
    is_mut.init_slice(tid, slice_is_mut)
    return tid


@functools.cache
def get_fn_type(
        arg_tid: identity.TID, ret_tid: identity.TID,
        ses: side_effects.SES
) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Fn)
    elem.init_func(tid, arg_tid, ret_tid)
    side_effects.init(tid, ses)
    return tid


@functools.cache
def get_tuple_type(elem_tid_iterable: Tuple[identity.TID]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Tuple)
    elem.init_tuple(tid, elem_tid_iterable)
    return tid


@functools.cache
def get_struct_type(field_elem_info_iterable: Tuple[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Struct)
    elem.init_struct(tid, field_elem_info_iterable)
    return tid


@functools.cache
def get_union_type(field_elem_info_iterable: Tuple[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Union)
    elem.init_union(tid, field_elem_info_iterable)
    return tid


@functools.cache
def get_enum_type(field_elem_info_iterable: Tuple[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Enum)
    elem.init_enum(tid, field_elem_info_iterable)
    return tid


#
# NOTE: module creation is not cached, because we want each module to have a unique type.
#

def new_module_type(field_elem_info_iterable: Tuple[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Module)
    elem.init_module(tid, field_elem_info_iterable)
    return tid


#
# NOTE: variable creation is not cached, even if the created variables share a name.
#       this is because no two variables are structurally equal.
#


def new_bound_var(name: str) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.BoundVar)
    spelling.init_var_name(tid, name)
    return tid


def new_free_var(name: str) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.FreeVar)
    spelling.init_var_name(tid, name)
    return tid
