// this module models global value variables (each with a `VID`)
// FIXME: 
//  - rename VID to ValID
//  - create a Mutator object that stores a changing VID
//  - require array, pointer, and slice to be composed of a vector of Mutator objects
//  - this way, contents of ValIDs are immutable, whereas Mutators encapsulate all changes.

#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>

#include "id-mval.hh"
#include "id-mast.hh"
#include "id-mtype.hh"
#include "id-intern.hh"
#include "id-vcell.hh"
#include "id-modules.hh"
#include "shared-enums.hh"

namespace monomorphizer::mval {

    extern VID const NULL_VID;
    extern size_t const MAX_VAL_HASH_BYTE_COUNT;

    enum ValueKind {
        VK_ERROR = 0,

        // immutable body types:
        VK_UNIT,
        VK_U1, VK_U8, VK_U16, VK_U32, VK_U64,
        VK_S8, VK_S16, VK_S32, VK_S64,
        VK_F32, VK_F64,
        VK_STRING,
        VK_TUPLE,
        VK_POINTER,
        VK_ARRAY,
        VK_SLICE,
        VK_FUNCTION
    };

    union ValueInfo {
        bool u1;
        uint8_t u8;
        uint16_t u16;
        uint32_t u32;
        uint64_t u64;
        int8_t s8;
        int16_t s16;
        int32_t s32;
        int64_t s64;
        float f32;
        double f64;
        size_t string_info_index;
        size_t sequence_info_index;
        size_t func_info_index;
        size_t ptr_info_index;
        size_t slice_info_index;
        size_t array_info_index;
    };

    struct CtxEnclosedId {
        intern::IntStr name;
        size_t target;
        // NOTE: `target` is either an mtype::TID or an mval::VID

        inline
        CtxEnclosedId()
        :   name(UNIVERSAL_NULL_ID),
            target(UNIVERSAL_NULL_ID)
        {}

        inline
        CtxEnclosedId(intern::IntStr enclosed_name, size_t enclosed_target)
        :   name(enclosed_name),
            target(enclosed_target)
        {}
    };

    struct FuncInfo {
        uint32_t arg_name_count;
        uint32_t ctx_enclosed_id_count;
        intern::IntStr* arg_name_array;
        CtxEnclosedId* ctx_enclosed_id_array;
        mast::ExpID body_exp_id;
        MonoModID mono_mod_id;

        inline
        FuncInfo(
            uint32_t new_arg_name_count,
            uint32_t new_ctx_enclosed_id_count,
            intern::IntStr* mv_arg_name_array,
            CtxEnclosedId* mv_ctx_enclosed_id_array,
            mast::ExpID new_body_exp_id,
            MonoModID new_mono_mod_id
        )
        :   arg_name_count(new_arg_name_count),
            ctx_enclosed_id_count(new_ctx_enclosed_id_count),
            arg_name_array(mv_arg_name_array),
            ctx_enclosed_id_array(mv_ctx_enclosed_id_array),
            body_exp_id(new_body_exp_id),
            mono_mod_id(new_mono_mod_id)
        {}
    };

}

namespace monomorphizer::mval {

    // value constructors:
    VID get_unit();
    VID push_u1(bool v);
    VID push_u8(uint8_t v);
    VID push_u16(uint16_t v);
    VID push_u32(uint32_t v);
    VID push_u64(uint64_t v);
    VID push_s8(int8_t v);
    VID push_s16(int16_t v);
    VID push_s32(int32_t v);
    VID push_s64(int64_t v);
    VID push_f32(float v);
    VID push_f64(double v);
    VID push_str(size_t code_point_count, int* mv_code_point_array);
    VID push_tuple(size_t elem_id_count, VID* mv_elem_id_array);
    VID push_function(
        uint32_t arg_name_count,
        intern::IntStr* mv_arg_name_array,
        uint32_t ctx_enclosed_id_count,
        CtxEnclosedId* mv_ctx_enclosed_id_array,
        mast::ExpID body_exp_id,
        MonoModID container_mono_mod_id
    );
    VID push_pointer(
        vcell::VCellID vcell_id,
        bool is_mut
    );
    VID push_array(
        size_t vcell_id_count,
        vcell::VCellID* mv_vcell_id_array,
        bool is_mut
    );
    VID push_slice(
        size_t vcell_id_count,
        vcell::VCellID* mv_vcell_id_array,
        bool is_mut
    );

    // property accessors:
    ValueKind value_kind(VID value_id);
    ValueInfo value_info(VID value_id);
    size_t get_seq_count(size_t sequence_info_index);
    std::optional<VID> get_seq_elem1(size_t seq_info_index, size_t index);
    std::optional<VID> get_seq_elem2(VID tuple_val_id, size_t index);
    bool get_seq_elem1_compatibility(size_t seq_info_index, size_t index, VID* out_vid);
    bool get_seq_elem2_compatibility(VID tuple_val_id, size_t index, VID* out_vid);
    FuncInfo* get_func_info(size_t func_info_index);
    vcell::VCellID get_ptr_vcell(size_t ptr_info_index);
    size_t count_array_vcells(size_t array_info_index);
    size_t count_slice_vcells(size_t array_info_index);
    vcell::VCellID get_array_vcell(size_t array_info_index, size_t index);
    vcell::VCellID get_slice_vcell(size_t array_info_index, size_t index);
    size_t count_str_code_points(size_t str_info_index);
    int get_str_code_point_at(size_t str_info_index, size_t code_point_index);

    // equality:
    bool equals(VID v1, VID v2);

}
