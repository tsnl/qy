"""
This system obtains type that make up other type, i.e. type 'elements'.
- e.g. arg and return type for functions
- e.g. field type for structs, unions, and enums
- e.g. pointed type for pointers, arrays, and slices.
"""

from typing import *
import dataclasses
import copy

from . import identity
from . import kind


components: Dict[identity.TID, "ProjComponent"] = {}


@dataclasses.dataclass
class ProjComponent(object):
    elem_info_tuple: Tuple["ElemInfo"]
    field_name_index_lut: Optional[Dict[str, int]] = None


@dataclasses.dataclass
class ElemInfo:
    name: Optional[str]
    tid: identity.TID
    is_type_field: bool = False

    def __hash__(self):
        assert isinstance(self.name, str)
        assert isinstance(self.tid, identity.TID)
        assert isinstance(self.is_type_field, bool)
        return hash((self.name, self.tid, self.is_type_field))


def help_init_any(
        tid: identity.TID,
        elem_info_tuple, allow_type_fields=False
) -> ProjComponent:
    assert isinstance(elem_info_tuple, tuple)
    assert all(map(lambda it: isinstance(it, ElemInfo), elem_info_tuple))

    # checking elem_info_tuples:
    if not allow_type_fields:
        for elem_info in elem_info_tuple:
            assert not elem_info.is_type_field

    # creating the component with defaults:
    new_component = ProjComponent(elem_info_tuple)
    components[tid] = new_component

    # assembling the [name] -> index look-up-table:
    new_component.field_name_index_lut = {}
    for elem_info_index, elem_info in enumerate(elem_info_tuple):
        if elem_info.name is not None:
            new_component.field_name_index_lut[elem_info.name] = elem_info_index

    return new_component


#
# Interface:
#

def init_ptr(ptr_tid: identity.TID, ptd_tid: identity.TID):
    return help_init_any(
        ptr_tid,
        elem_info_tuple=(ElemInfo("ptd", ptd_tid),)
    )


def init_array(ptr_tid: identity.TID, elem_tid: identity.TID):
    return help_init_any(
        ptr_tid,
        elem_info_tuple=(ElemInfo(None, elem_tid),)
    )


def init_slice(ptr_tid: identity.TID, elem_tid: identity.TID):
    return help_init_any(
        ptr_tid,
        elem_info_tuple=(ElemInfo(None, elem_tid),)
    )


def init_func(tid: identity.TID, arg_tid: identity.TID, ret_tid: identity.TID):
    return help_init_any(
        tid,
        elem_info_tuple=(ElemInfo(None, arg_tid), ElemInfo(None, ret_tid))
    )


def init_tuple(ptr_tid: identity.TID, elem_tid_iterable: Iterable[identity.TID]):
    return help_init_any(
        ptr_tid,
        elem_info_tuple=tuple((ElemInfo(None, elem_tid) for elem_tid in elem_tid_iterable))
    )


def init_struct(tid: identity.TID, field_elem_info_tuple):
    return help_init_any(tid, elem_info_tuple=field_elem_info_tuple)


def init_union(tid: identity.TID, field_elem_info_tuple):
    return help_init_any(tid, elem_info_tuple=field_elem_info_tuple)


def init_enum(tid: identity.TID, field_elem_info_tuple):
    return help_init_any(tid, elem_info_tuple=field_elem_info_tuple)


def init_module(tid: identity.TID, field_elem_info_tuple):
    return help_init_any(tid, elem_info_tuple=field_elem_info_tuple, allow_type_fields=True)


def count(tid: identity.TID) -> int:
    return len(components[tid].elem_info_tuple)


def copy_elem_info_tuple(tid: identity.TID) -> Tuple[ElemInfo]:
    return copy.copy(components[tid].elem_info_tuple)


def tid_of_fn_arg(tid: identity.TID) -> identity.TID:
    return components[tid].elem_info_tuple[0].tid


def tid_of_fn_ret(tid: identity.TID) -> identity.TID:
    return components[tid].elem_info_tuple[1].tid


def field_name_at_ix(algebraic_tid: identity.TID, field_index: int) -> str:
    return components[algebraic_tid].elem_info_tuple[field_index].name


def tid_of_field_ix(algebraic_tid: identity.TID, field_index: int) -> identity.TID:
    assert field_index >= 0
    return components[algebraic_tid].elem_info_tuple[field_index].tid


def is_type_field_at_field_ix(algebraic_tid: identity.TID, field_index: int) -> bool:
    return components[algebraic_tid].elem_info_tuple[field_index].is_type_field


def field_ix_of_name(algebraic_tid: identity.TID, field_name: str) -> int:
    if components[algebraic_tid].field_name_index_lut is not None:
        # cache present for TIDs of this kind
        return components[algebraic_tid].field_name_index_lut.get(field_name, None)
    else:
        # no cache, no fields.
        raise NotImplementedError(f"No field index cache for type of kind {kind.of(algebraic_tid)}")


def tid_of_ptd(tid: identity.TID) -> identity.TID:
    assert kind.of(tid) in (kind.TK.Pointer, kind.TK.Array, kind.TK.Slice)
    return components[tid].elem_info_tuple[0].tid
