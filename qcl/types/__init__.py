"""
Each type is just a unique integer ID.
Each sub-module of this package manages a system, or a co-located facet some types.
We guarantee a structural type system using `functools.cache` + a nominal wrapper to create types.
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


@functools.cache
def new_int_type(width_in_bytes: int, is_unsigned=False) -> identity.TID:
    tid = identity.mint()
    if is_unsigned:
        kind.init(tid, kind.TK.UnsignedInt)
    else:
        kind.init(tid, kind.TK.SignedInt)
    scalar_width_in_bytes.init(tid, width_in_bytes)
    return tid


@functools.cache
def new_float_type(width_in_bytes: int) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Float)
    scalar_width_in_bytes.init(tid, width_in_bytes)
    return tid


@functools.cache
def new_str_type() -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.String)
    return tid


@functools.cache
def new_ptr_type(ptd_tid: identity.TID, ptr_is_mut) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Pointer)
    elem.init_ptr(tid, ptd_tid)
    is_mut.init_ptr(tid, ptr_is_mut)
    return tid


@functools.cache
def new_array_type(ptd_tid: identity.TID, array_is_mut) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Array)
    elem.init_array(tid, ptd_tid)
    is_mut.init_array(tid, array_is_mut)
    return tid


@functools.cache
def new_slice_type(ptd_tid: identity.TID, slice_is_mut) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Slice)
    elem.init_slice(tid, ptd_tid)
    is_mut.init_slice(tid, slice_is_mut)
    return tid


@functools.cache
def new_fn_type(
        arg_tid: identity.TID, ret_tid: identity.TID,
        ses: side_effects.SES
) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Fn)
    elem.init_func(tid, arg_tid, ret_tid)
    side_effects.init(tid, ses)
    return tid


@functools.cache
def new_tuple_type(elem_tid_iterable: Iterable[identity.TID]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Tuple)
    elem.init_tuple(tid, elem_tid_iterable)
    return tid


@functools.cache
def new_struct_type(field_elem_info_iterable: Iterable[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Struct)
    elem.init_struct(tid, field_elem_info_iterable)
    return tid


@functools.cache
def new_union_type(field_elem_info_iterable: Iterable[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Union)
    elem.init_union(tid, field_elem_info_iterable)
    return tid


@functools.cache
def new_enum_type(field_elem_info_iterable: Iterable[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Enum)
    elem.init_enum(tid, field_elem_info_iterable)
    return tid


@functools.cache
def new_module_type(field_elem_info_iterable: Iterable[elem.ElemInfo]) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Module)
    elem.init_enum(tid, field_elem_info_iterable)
    return tid


@functools.cache
def new_bound_var(name: str) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.BoundVar)
    spelling.init_var_name(tid, name)
    return tid


@functools.cache
def new_free_var(name: str) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.FreeVar)
    spelling.init_var_name(tid, name)
    return tid
