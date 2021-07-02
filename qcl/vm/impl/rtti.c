#include <assert.h>
#include <stdlib.h>
#include <string.h>

#include "rtti.h"
#include "table.h"
#include "core.h"

typedef struct AdtInfo AdtInfo;
typedef struct UnionInfo UnionInfo;
typedef struct FnInfo FnInfo;
typedef struct PtrInfo PtrInfo;
typedef struct ArrayInfo ArrayInfo;
typedef struct SliceInfo SliceInfo;
typedef union TypeInfo TypeInfo;

RtTypeID mint_rttid(RttiManager* rm, uint8_t kind);

//
//
// Implementation:
//
//

struct RttiManager {
    RtTypeID rttid_counter;
    size_t ptr_size_in_bytes;

    Table* kind_table;      // Table[uint8_t/ValKind]
    Table* size_table;      // Table[uint64_t]
    Table* info_table;      // Table[TypeInfo]

    RtTypeID unit_rttid;
    RtTypeID string_rttid;

    RtTypeID u8_rttid;
    RtTypeID u16_rttid;
    RtTypeID u32_rttid;
    RtTypeID u64_rttid;

    RtTypeID s8_rttid;
    RtTypeID s16_rttid;
    RtTypeID s32_rttid;
    RtTypeID s64_rttid;

    RtTypeID f32_rttid;
    RtTypeID f64_rttid;
};
struct AdtInfo {
    size_t elem_count;
    RtTypeID* elem_rttids;
};
struct FnInfo {
    RtTypeID arg_rttid;
    RtTypeID ret_rttid;
};
struct PtrInfo {
    RtTypeID ptd_rttid;
    bool is_mut;
};
union TypeInfo {
    AdtInfo adt;
    FnInfo fn;
    PtrInfo ptr;
};

//
//
// Function definitions:
//
//

RtTypeID mint_rttid(RttiManager* rm, uint8_t kind, uint64_t size_in_bytes) {
    // each type is supported by 3 parallel arrays/properties:
    //  - 'kind': every type has a 'kind', used to distinguish unions
    //  - 'size': size in bytes
    //  - 'info': union of properties, discriminated by kind.

    RtTypeID rttid = rm->rttid_counter++;
    
    uint8_t* kind_p = tab_gp(rm->kind_table, rttid);
    *kind_p = kind;
    
    uint64_t* size_p = tab_gp(rm->size_table, rttid);
    *size_p = size_in_bytes;

    // TypeInfo* ti_p = tab_gp(rm->info_table, rttid);
    // - no init performed by default
    
    return rttid;
}

RttiManager* rtti_mgr_new() {
    size_t max_type_count = 1024*1024;

    RttiManager* rm = malloc(sizeof(RttiManager));

    // first, initializing properties needed to mint new runtime types:
    rm->rttid_counter = 1;
    rm->ptr_size_in_bytes = 8;
    rm->kind_table = tab_new(sizeof(uint8_t), 64, max_type_count / 64);
    rm->size_table = tab_new(sizeof(size_t), 8, max_type_count / 8);

    // minting run-time types for primitives:
    {
        // simplest basic types:
        rm->unit_rttid = mint_rttid(rm, VAL_UNIT, 0);
        rm->string_rttid = mint_rttid(rm, VAL_STRING, 16);
        
        // unsigned ints:
        rm->u8_rttid = mint_rttid(rm, VAL_UINT, 1);
        rm->u16_rttid = mint_rttid(rm, VAL_UINT, 2);
        rm->u32_rttid = mint_rttid(rm, VAL_UINT, 4);
        rm->u64_rttid = mint_rttid(rm, VAL_UINT, 8);
        
        // signed ints:
        rm->s8_rttid = mint_rttid(rm, VAL_SINT, 1);
        rm->s16_rttid = mint_rttid(rm, VAL_SINT, 2);
        rm->s32_rttid = mint_rttid(rm, VAL_SINT, 4);
        rm->s64_rttid = mint_rttid(rm, VAL_SINT, 8);

        // floats:
        rm->f32_rttid = mint_rttid(rm, VAL_FLOAT, 4);
        rm->f64_rttid = mint_rttid(rm, VAL_FLOAT, 8);
    }

    return rm;
}
void rtti_mgr_del(RttiManager* rtti_mgr) {
    tab_del(rtti_mgr->kind_table);
    tab_del(rtti_mgr->size_table);
    free(rtti_mgr);
}

//
// type ID constructors:
//

RtTypeID help_new_adt_rttid(RttiManager* rm, ValueKind vk, size_t elem_count, RtTypeID* elem_rttids);
RtTypeID help_new_ptr_rttid(RttiManager* rm, ValueKind vk, RtTypeID ptd_rttid, bool is_mut);

RtTypeID get_unit_rttid(RttiManager* rm) {
    return rm->unit_rttid;
}
RtTypeID get_string_rttid(RttiManager* rm) {
    return rm->string_rttid;
}
RtTypeID get_int_rttid(RttiManager* rm, int lg2_width_in_bytes, bool is_signed) {
    if (is_signed) {
        switch (lg2_width_in_bytes) {
            case 0: {
                return rm->u8_rttid;
            } break;
            case 1: {
                return rm->u16_rttid;
            } break;
            case 2: {
                return rm->u32_rttid;
            } break;
            case 3: {
                return rm->u64_rttid;
            } break;
            default: {
                assert(0 && "Invalid unsigned int width");
            } break;
        }
    } else {
        switch (lg2_width_in_bytes) {
            case 0: {
                return rm->s8_rttid;
            } break;
            case 1: {
                return rm->s16_rttid;
            } break;
            case 2: {
                return rm->s32_rttid;
            } break;
            case 3: {
                return rm->s64_rttid;
            } break;
            default: {
                assert(0 && "Invalid signed int width");
            } break;
        }
    }
}
RtTypeID get_float_rttid(RttiManager* rm, int lg2_width_in_bytes) {
    switch (lg2_width_in_bytes) {
        case 2: {
            return rm->f32_rttid;
        } break;
        case 3: {
            return rm->f64_rttid;
        } break;
        default: {
            assert(0 && "Invalid float width");
        } break;
    }
}
RtTypeID new_tuple_rttid(RttiManager* rm, size_t elem_count, RtTypeID* elem_rttids) {
    return help_new_adt_rttid(rm, VAL_TUPLE, elem_count, elem_rttids);
}
RtTypeID new_union_rttid(RttiManager* rm, size_t elem_count, RtTypeID* elem_rttids) {
    return help_new_adt_rttid(rm, VAL_UNION, elem_count, elem_rttids);
}
RtTypeID new_fn_rttid(RttiManager* rm, RtTypeID arg_tid, RtTypeID ret_tid) {
    RtTypeID rttid = mint_rttid(rm, VAL_FN, rm->ptr_size_in_bytes);
    
    TypeInfo* ti_p = tab_gp(rm->info_table, rttid);
    ti_p->fn.arg_rttid = arg_tid;
    ti_p->fn.ret_rttid = ret_tid;
    
    return rttid;
}
RtTypeID new_ptr_rttid(RttiManager* rm, RtTypeID ptd_tid, bool is_mut) {
    return help_new_ptr_rttid(rm, VAL_PTR, ptd_tid, is_mut);
}
RtTypeID new_array_rttid(RttiManager* rm, RtTypeID elem_tid, bool is_mut) {
    return help_new_ptr_rttid(rm, VAL_ARRAY, elem_tid, is_mut);
}
RtTypeID new_slice_rttid(RttiManager* rm, RtTypeID elem_tid, bool is_mut) {
    return help_new_ptr_rttid(rm, VAL_SLICE, elem_tid, is_mut);
}
RtTypeID help_new_adt_rttid(RttiManager* rm, ValueKind vk, size_t elem_count, RtTypeID* elem_rttids) {
    size_t net_size = 0;
    for (size_t i = 0; i < elem_count; i++) {
        RtTypeID elem_rttid = elem_rttids[i];
        net_size += get_size_of_rttid(rm, elem_rttid);
    }

    RtTypeID adt_rttid = mint_rttid(rm, vk, net_size);
    TypeInfo* ti_p = tab_gp(rm->info_table, adt_rttid);
    ti_p->adt.elem_count = elem_count;
    ti_p->adt.elem_rttids = memcpy(
        malloc(sizeof(RtTypeID) * elem_count), 
        elem_rttids, sizeof(RtTypeID) * elem_count
    );

    return adt_rttid;
}
RtTypeID help_new_ptr_rttid(RttiManager* rm, ValueKind vk, RtTypeID ptd_rttid, bool is_mut) {
    RtTypeID rttid = mint_rttid(rm, vk, rm->ptr_size_in_bytes);
    
    TypeInfo* ti_p = tab_gp(rm->info_table, rttid);
    ti_p->ptr.ptd_rttid = ptd_rttid;
    ti_p->ptr.is_mut = is_mut;

    return rttid;
}

//
// Property getters:
//

size_t get_size_of_rttid(RttiManager* rm, RtTypeID tid) {
    size_t* size_p = tab_gp(rm->size_table, tid);
    return *size_p;
}
ValueKind get_kind_of_rttid(RttiManager* rm, RtTypeID tid) {
    uint8_t* v_p = tab_gp(rm->kind_table, tid);
    return (ValueKind)*v_p;
}
RtTypeID get_ptd_of_ptr_rttid(RttiManager* rm, RtTypeID tid) {
    TypeInfo* ti_p = tab_gp(rm->info_table, tid);
    return ti_p->ptr.ptd_rttid;
}
bool get_mut_of_ptr_rttid(RttiManager* rm, RtTypeID tid) {
    TypeInfo* ti_p = tab_gp(rm->info_table, tid);
    return ti_p->ptr.is_mut;
}
size_t get_elem_count_of_adt_rttid(RttiManager* rm, RtTypeID container_tid) {
    ValueKind container_vk = get_kind_of_rttid(rm, container_tid);
    assert(
        container_vk == VAL_TUPLE ||
        container_vk == VAL_UNION
    );
    TypeInfo* ti_p = tab_gp(rm->info_table, container_tid);
    return ti_p->adt.elem_count;
}
RtTypeID get_elem_tid_of_adt_rttid(RttiManager* rm, RtTypeID container_tid, size_t elem_index) {
    ValueKind container_vk = get_kind_of_rttid(rm, container_tid);
    assert(
        container_vk == VAL_TUPLE ||
        container_vk == VAL_UNION
    );
    TypeInfo* ti_p = tab_gp(rm->info_table, container_tid);
    assert(elem_index < ti_p->adt.elem_count && "RTTI: get elem TID out of bounds");
    return ti_p->adt.elem_rttids[elem_index];
}
RtTypeID get_arg_tid_of_fn_rttid(RttiManager* rm, RtTypeID fn_tid) {
    assert(get_kind_of_rttid(rm, fn_tid) == VAL_FN);
    TypeInfo* ti_p = tab_gp(rm->info_table, fn_tid);
    return ti_p->fn.arg_rttid;
}
RtTypeID get_ret_tid_of_fn_rttid(RttiManager* rm, RtTypeID fn_tid) {
    assert(get_kind_of_rttid(rm, fn_tid) == VAL_FN);
    TypeInfo* ti_p = tab_gp(rm->info_table, fn_tid);
    return ti_p->fn.ret_rttid;
}

//
// comparison:
//

bool are_types_equal(RttiManager* rm, RtTypeID lhs_tid, RtTypeID rhs_tid) {
    // level 1: kinds checks
    ValueKind lhs_vk = get_kind_of_rttid(rm, lhs_tid);
    ValueKind rhs_vk = get_kind_of_rttid(rm, rhs_tid);
    if (lhs_vk != rhs_vk) {
        return false;
    }

    // level 2: kind-dependent checks:
    ValueKind vk = lhs_vk;
    switch (vk) {
        // for simple types, we maintain unique TIDs:
        case VAL_UNIT:
        case VAL_STRING:
        case VAL_UINT:
        case VAL_SINT:
        case VAL_FLOAT: {
            return lhs_tid == rhs_tid;
        }

        // for complex types, we do not guarantee unique TIDs, so we need
        // to recursively compare:
        case VAL_PTR:
        case VAL_ARRAY:
        case VAL_SLICE: {
            RtTypeID lhs_ptd_rttid = get_ptd_of_ptr_rttid(rm, lhs_tid);
            RtTypeID rhs_ptd_rttid = get_ptd_of_ptr_rttid(rm, rhs_tid);
            return are_types_equal(rm, lhs_ptd_rttid, rhs_ptd_rttid);
        }
        case VAL_TUPLE:
        case VAL_UNION: {
            size_t lhs_elem_count = get_elem_count_of_adt_rttid(rm, lhs_tid);
            size_t rhs_elem_count = get_elem_count_of_adt_rttid(rm, rhs_tid);
            if (lhs_elem_count != rhs_elem_count) {
                return false;
            }
            size_t elem_count = lhs_elem_count;
            for (size_t i_elem = 0; i_elem < elem_count; i_elem++) {
                RtTypeID lhs_elem_tid = get_elem_tid_of_adt_rttid(rm, lhs_tid, i_elem);
                RtTypeID rhs_elem_tid = get_elem_tid_of_adt_rttid(rm, rhs_tid, i_elem);
                if (!are_types_equal(rm, lhs_elem_tid, rhs_elem_tid)) {
                    return false;
                }
            }
            return true;
        }
        case VAL_FN: {
            RtTypeID lhs_arg_rttid = get_arg_tid_of_fn_rttid(rm, lhs_tid);
            RtTypeID lhs_ret_rttid = get_ret_tid_of_fn_rttid(rm, lhs_tid);
            RtTypeID rhs_arg_rttid = get_arg_tid_of_fn_rttid(rm, rhs_tid);
            RtTypeID rhs_ret_rttid = get_ret_tid_of_fn_rttid(rm, rhs_tid);
            return (
                are_types_equal(rm, lhs_arg_rttid, rhs_arg_rttid) &&
                are_types_equal(rm, lhs_ret_rttid, rhs_ret_rttid)
            );
        }
        default: {
            assert(0 && "Unknown ValueKind in `are_types_equal`");
        }
    }
}