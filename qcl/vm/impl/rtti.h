// NOTE: the RTTI RtTypeID (RuntimeTypeID) is different than the compiler TypeID.
//      - unlike the compiler TID, RtTypeIDs are not guaranteed to be structurally unique--
//        instead, we use a nominal system and explicitly compare elements.

#pragma once

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include "core.h"

typedef size_t RtTypeID;
typedef struct RttiManager RttiManager;

RttiManager* rtti_mgr_new();
void rtti_mgr_del(RttiManager* rtti_mgr);

RtTypeID get_unit_rttid(RttiManager* rm);
RtTypeID get_string_rttid(RttiManager* rm);
RtTypeID get_int_rttid(RttiManager* rm, int lg2_width_in_bytes, bool is_signed);
RtTypeID get_float_rttid(RttiManager* rm, int lg2_width_in_bytes);
RtTypeID new_tuple_rttid(RttiManager* rm, size_t elem_count, RtTypeID* elem_tids);
RtTypeID new_union_rttid(RttiManager* rm, size_t elem_count, RtTypeID* elem_tids);
RtTypeID new_fn_rttid(RttiManager* rm, RtTypeID arg_tid, RtTypeID ret_tid);
RtTypeID new_ptr_rttid(RttiManager* rm, RtTypeID ptr_tid, bool is_mut);
RtTypeID new_array_rttid(RttiManager* rm, RtTypeID elem_tid, bool is_mut);
RtTypeID new_slice_rttid(RttiManager* rm, RtTypeID elem_tid, bool is_mut);

size_t get_size_of_rttid(RttiManager* rm, RtTypeID tid);
ValueKind get_kind_of_rttid(RttiManager* rm, RtTypeID tid);
RtTypeID get_ptd_of_ptr_rttid(RttiManager* rm, RtTypeID tid);
bool get_mut_of_ptr_rttid(RttiManager* rm, RtTypeID tid);
RtTypeID get_elem_tid_of_adt_rttid(RttiManager* rm, RtTypeID container_tid, size_t elem_index);
size_t get_elem_count_of_adt_rttid(RttiManager* rm, RtTypeID container_tid);
RtTypeID get_arg_tid_of_fn_rttid(RttiManager* rm, RtTypeID fn_tid);
RtTypeID get_ret_tid_of_fn_rttid(RttiManager* rm, RtTypeID fn_tid);

//
// comparison:
//

bool are_types_equal(RttiManager* rm, RtTypeID lhs_tid, RtTypeID rhs_tid);

//
// TODO
//  - allow ses to be passed to fns.
