#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>

#include "id-mast.hh"
#include "id-mval.hh"
#include "id-intern.hh"
#include "shared-enums.hh"

namespace monomorphizer::mval {

    extern ValueID const NULL_VID;
    extern size_t const MAX_VAL_HASH_BYTE_COUNT;

    enum ValueKind {
        VK_ERROR = 0,
        VK_UNIT,
        VK_U1, VK_U8, VK_U16, VK_U32, VK_U64,
        VK_S8, VK_S16, VK_S32, VK_S64,
        VK_F32, VK_F64,
        VK_STRING,
        VK_TUPLE,
        VK_ARRAY,
        VK_SLICE,
        VK_FUNCTION

        // todo: add pointers
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
    };

    struct CtxEnclosedId {
        intern::IntStr name;
        size_t target;
        // NOTE: `target` is either an mtype::TID or an mval::ValueID

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

        inline
        FuncInfo(
            uint32_t new_arg_name_count,
            uint32_t new_ctx_enclosed_id_count,
            intern::IntStr* mv_arg_name_array,
            CtxEnclosedId* mv_ctx_enclosed_id_array,
            mast::ExpID new_body_exp_id
        )
        :   arg_name_count(new_arg_name_count),
            ctx_enclosed_id_count(new_ctx_enclosed_id_count),
            arg_name_array(mv_arg_name_array),
            ctx_enclosed_id_array(mv_ctx_enclosed_id_array),
            body_exp_id(new_body_exp_id)
        {}
    };

}

namespace monomorphizer::mval {

    // value constructors:
    ValueID get_unit();
    ValueID push_u1(bool v);
    ValueID push_u8(uint8_t v);
    ValueID push_u16(uint16_t v);
    ValueID push_u32(uint32_t v);
    ValueID push_u64(uint64_t v);
    ValueID push_s8(int8_t v);
    ValueID push_s16(int16_t v);
    ValueID push_s32(int32_t v);
    ValueID push_s64(int64_t v);
    ValueID push_f32(float v);
    ValueID push_f64(double v);
    ValueID push_str(size_t code_point_count, int* mv_code_point_array);
    ValueID push_tuple(size_t elem_id_count, ValueID* mv_elem_id_array);
    ValueID push_function(
        uint32_t arg_name_count,
        intern::IntStr* mv_arg_name_array,
        uint32_t ctx_enclosed_id_count,
        CtxEnclosedId* mv_ctx_enclosed_id_array,
        mast::ExpID body_exp_id
    );

    // property accessors:
    ValueKind value_kind(ValueID value_id);
    ValueInfo value_info(ValueID value_id);
    std::optional<ValueID> get_seq_elem(size_t sequence_info_index, size_t index);
    FuncInfo* get_func_info(size_t func_info_index);

    // equality:
    bool equals(ValueID v1, ValueID v2);

}
