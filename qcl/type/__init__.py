"""
Each type is just a unique integer ID.
Each sub-module of this package manages a system, or a co-located facet some type.
We guarantee a structural type system using `functools.cache` + a nominal wrapper to create type.
"""

import functools

from typing import *
import copy

from . import identity
from . import kind
from . import elem
from . import scalar_width_in_bits
from . import mem_window
from . import spelling
from . import side_effects
from . import free
from . import closure_spec
from . import lifetime


#
# Helpers:
#

def _get_cached_type(cache, ctor, arg_key, ctor_takes_arg_key_directly=False):
    opt_val = cache.get(arg_key, None)
    if opt_val is not None:
        return opt_val
    else:
        if ctor_takes_arg_key_directly:
            val = ctor(arg_key)
        else:
            val = ctor(*arg_key)
        cache[arg_key] = val
        return val


#
# Unit type:
#

def get_unit_type():
    return _unit_tid


def _new_unit_type():
    tid = identity.mint()
    kind.init(tid, kind.TK.Unit)
    return tid


_unit_tid = _new_unit_type()


#
# String types:
#

def get_str_type() -> identity.TID:
    return _str_tid


def _new_str_type() -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.String)
    return tid


_str_tid = _new_str_type()


#
# Int types:
#


def get_int_type(width_in_bits: int, is_unsigned=False) -> identity.TID:
    return _int_tid_map[width_in_bits, is_unsigned]


def _new_int_type_map():
    def new_int_type(width_in_bits: int, is_unsigned=False) -> identity.TID:
        tid = identity.mint()
        if is_unsigned:
            kind.init(tid, kind.TK.UnsignedInt)
        else:
            kind.init(tid, kind.TK.SignedInt)
        scalar_width_in_bits.init(tid, width_in_bits)
        return tid

    def bit_widths(is_unsigned):
        if is_unsigned:
            return 1, 8, 16, 32, 64, 128
        else:
            return 8, 16, 32, 64, 128

    return {
        (width_in_bits, is_unsigned): new_int_type(width_in_bits, is_unsigned)
        for is_unsigned in (False, True)
        for width_in_bits in bit_widths(is_unsigned)
    }


_int_tid_map = _new_int_type_map()


#
# Float types:
#

def get_float_type(width_in_bytes: int) -> identity.TID:
    return _float_tid_map[width_in_bytes]


def _new_float_type_map():
    def new_float_type(width_in_bits):
        tid = identity.mint()
        kind.init(tid, kind.TK.Float)
        scalar_width_in_bits.init(tid, width_in_bits)
        return tid

    return {
        i: new_float_type(i)
        for i in (
            16,
            32,
            64
        )
    }


_float_tid_map = _new_float_type_map()


#
# Pointer types:
#

_ptr_tid_map = {}


def get_ptr_type(ptd_tid: identity.TID, ptr_is_mut: bool) -> identity.TID:
    return _get_cached_type(
        _ptr_tid_map,
        _new_ptr_type,
        (ptd_tid, ptr_is_mut)
    )


def _new_ptr_type(ptd_tid: identity.TID, ptr_is_mut: bool) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Pointer)
    elem.init_ptr(tid, ptd_tid)
    mem_window.init(tid, ptr_is_mut)
    return tid


#
# Array types:
#

_array_tid_map = {}


def get_array_type(
        ptd_tid: identity.TID,
        size_tid: identity.TID,
        array_is_mut: bool
) -> identity.TID:
    return _get_cached_type(
        _array_tid_map,
        _new_array_tid,
        (ptd_tid, size_tid, array_is_mut)
    )


def _new_array_tid(ptd_tid: identity.TID, size_tid: identity.TID, array_is_mut: bool):
    tid = identity.mint()
    kind.init(tid, kind.TK.Array)
    elem.init_array(tid, ptd_tid, size_tid)
    mem_window.init(tid, array_is_mut)
    return tid


#
# Slice types:
#

_slice_tid_map = {}


def get_slice_type(
        ptd_tid: identity.TID,
        size_tid: identity.TID,
        slice_is_mut: bool
) -> identity.TID:
    return _get_cached_type(
        _slice_tid_map,
        _new_slice_type,
        (ptd_tid, size_tid, slice_is_mut)
    )


def _new_slice_type(
        ptd_tid: identity.TID,
        size_tid: identity.TID,
        slice_is_mut: bool
) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Slice)
    elem.init_slice(tid, ptd_tid, size_tid)
    mem_window.init(tid, slice_is_mut)
    return tid


#
# Function types:
#

_fn_tid_map = {}


def get_fn_type(
        arg_tid: identity.TID, ret_tid: identity.TID,
        ses: side_effects.SES,
        cs: closure_spec.CS
) -> identity.TID:
    return _get_cached_type(
        _fn_tid_map,
        _new_fn_type,
        (arg_tid, ret_tid, ses, cs)
    )


def _new_fn_type(
        arg_tid: identity.TID, ret_tid: identity.TID,
        ses: side_effects.SES,
        cs: closure_spec.CS
) -> identity.TID:
    assert ses is not None
    assert closure_spec is not None
    tid = identity.mint()
    kind.init(tid, kind.TK.Fn)
    elem.init_func(tid, arg_tid, ret_tid)
    closure_spec.init_func(tid, cs)
    side_effects.init(tid, ses)
    return tid


#
# Tuple types:
#

_tuple_tid_map = {}


def get_tuple_type(elem_tid_tuple: tuple) -> identity.TID:
    return _get_cached_type(
        _tuple_tid_map,
        _new_tuple_type,
        elem_tid_tuple,
        ctor_takes_arg_key_directly=True
    )


def _new_tuple_type(elem_tid_tuple: tuple) -> identity.TID:
    tid = identity.mint()
    kind.init(tid, kind.TK.Tuple)
    elem.init_tuple(tid, elem_tid_tuple)
    return tid


#
# Struct types:
#

_struct_tid_map = {}


def get_struct_type(field_elem_info_tuple) -> identity.TID:
    return _get_cached_type(
        _struct_tid_map,
        _new_struct_type,
        field_elem_info_tuple,
        ctor_takes_arg_key_directly=True
    )


def _new_struct_type(field_elem_info_tuple) -> identity.TID:
    assert isinstance(field_elem_info_tuple, tuple)

    tid = identity.mint()
    kind.init(tid, kind.TK.Struct)
    elem.init_struct(tid, copy.deepcopy(field_elem_info_tuple))
    return tid


#
# Union types:
#

_union_tid_map = {}


def get_union_type(field_elem_info_tuple) -> identity.TID:
    return _get_cached_type(
        _union_tid_map,
        _new_union_type,
        ctor_takes_arg_key_directly=True
    )


def _new_union_type(field_elem_info_tuple) -> identity.TID:
    assert isinstance(field_elem_info_tuple, tuple)

    tid = identity.mint()
    kind.init(tid, kind.TK.Union)
    elem.init_union(tid, copy.deepcopy(field_elem_info_tuple))
    return tid


#
#
# Un-cached types:
#
#

#
# NOTE: module creation is not cached, because we want each module to have a unique type.
#

def new_module_type(field_elem_info_tuple) -> identity.TID:
    assert isinstance(field_elem_info_tuple, tuple)

    tid = identity.mint()
    kind.init(tid, kind.TK.Module)
    elem.init_module(tid, copy.deepcopy(field_elem_info_tuple))
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
