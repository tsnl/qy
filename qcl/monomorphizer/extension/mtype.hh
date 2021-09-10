#pragma once

#include <cstddef>

#include "id-arg-list.hh"
#include "id-mtype.hh"
#include "id-mval.hh"
#include "shared-enums.hh"

namespace monomorphizer::mtype {

    void ensure_mtype_init();

    // TODO: create a `MType` module that...
    //  - is pretty much identical to the python `type` module
    //  - re-generates IDs for all relevant types
    //  - creates new IDs upon substitution as required

    // Like TIDs before, this system returns a unique ID for each type.
    // In other words,
    //  id1 == id2 <=> type(id1) == type(id2)

    enum TypeKind {
        TK_ERROR = 0,
        TK_UNIT,
        TK_U1, TK_U8, TK_U16, TK_U32, TK_U64,
        TK_S8, TK_S16, TK_S32, TK_S64,
        TK_F32, TK_F64,
        TK_STRING,
        TK_TUPLE,
        TK_POINTER,
        TK_ARRAY,
        TK_SLICE,
        TK_FUNCTION
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
        mval::ValVarID count_val_id, 
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
    size_t get_tuple_count(TID tuple_tid);
    arg_list::ArgListID get_tuple_arg_list(TID tuple_tid);

}
