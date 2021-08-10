#pragma once

#include <cstddef>

#include "id-arg-list.hh"
#include "id-mtype.hh"
#include "id-mval.hh"
#include "shared-enums.hh"

namespace monomorphizer::mtype {

    void ensure_init();

    // TODO: create a `MType` module that...
    //  - is pretty much identical to the python `type` module
    //  - re-generates IDs for all relevant types
    //  - creates new IDs upon substitution as required

    // Like TIDs before, this system returns a unique ID for each type.
    // In other words,
    //  id1 == id2 <=> type(id1) == type(id2)

    enum class TypeKind {
        Unit,
        U1, U8, U16, U32, U64,
        S8, S16, S32, S64,
        F32, F64,
        String,
        Tuple,
        Pointer,
        Array,
        Slice,
        Function
    };

    TID get_unit_tid();
    TID get_u1_tid();
    TID get_u8_tid();
    TID get_u16_tid();
    TID get_u32_tid();
    TID get_u64_tid();
    TID get_s8_tid();
    TID get_s16_tid();
    TID get_s32_tid();
    TID get_s64_tid();
    TID get_f32_tid();
    TID get_f64_tid();
    TID get_string_tid();
    TID get_tuple_tid(
        arg_list::ArgListID arg_list_id
    );
    TID get_ptr_tid(
        TID ptd_tid, 
        bool contents_is_mut
    );
    TID get_array_tid(
        TID ptd_tid, 
        mval::ValueID count_val_id, 
        bool contents_is_mut
    );
    TID get_slice_tid(
        TID ptd_tid, 
        bool contents_is_mut
    );
    TID get_function_tid(
        TID arg_tid, 
        TID ret_tid, 
        SES ses
    );

    TypeKind kind_of_tid(TID tid);

}
