#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>

#include "id-mval.hh"

namespace monomorphizer::mval {

    extern ValueID const NULL_VID;

    enum class ValueKind {
        Unit,
        U1, U8, U16, U32, U64,
        S8, S16, S32, S64,
        F32, F64,
        String,
        Tuple,
        Array,
        Slice

        // todo: add functions: body is just MAST code
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
    };

}

namespace monomorphizer::mval {

    extern size_t const MAX_VAL_HASH_BYTE_COUNT;

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

    // property accessors:
    ValueKind value_kind(ValueID value_id);
    ValueInfo value_info(ValueID value_id);
    std::optional<ValueID> get_seq_elem(size_t sequence_info_index, size_t index);

    // equality:
    bool equals(ValueID v1, ValueID v2);

}
