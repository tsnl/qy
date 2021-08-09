#pragma once

#include <cstddef>

#include "id-arg-list.hh"
#include "id-mtype.hh"
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

    MTypeID get_unit_tid();
    MTypeID get_u1_tid();
    MTypeID get_u8_tid();
    MTypeID get_u16_tid();
    MTypeID get_u32_tid();
    MTypeID get_u64_tid();
    MTypeID get_s8_tid();
    MTypeID get_s16_tid();
    MTypeID get_s32_tid();
    MTypeID get_s64_tid();
    MTypeID get_f32_tid();
    MTypeID get_f64_tid();
    MTypeID get_str_tid();
    MTypeID get_tuple_tid(arg_list::ArgListID arg_list_id);
    MTypeID get_ptr_tid(MTypeID ptd_tid, bool contents_is_mut);
    MTypeID get_array_tid(MTypeID ptd_tid, bool contents_is_mut);
    MTypeID get_slice_tid(MTypeID ptd_tid, bool contents_is_mut);
    MTypeID get_function_tid(MTypeID arg_tid, MTypeID ret_tid, SES ses);

}
