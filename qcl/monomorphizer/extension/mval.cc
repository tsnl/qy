#include "mval.hh"

#include <deque>
#include <cstddef>
#include <cstdint>
#include <string>

#include "panic.hh"

namespace monomorphizer::mval {

    size_t const MAX_VAL_HASH_BYTE_COUNT = 64 * 1024;

    struct StringInfo {
        size_t code_point_count;
        int* code_point_array;

        inline
        StringInfo(size_t code_point_count, int* mv_code_point_array)
        :   code_point_count(code_point_count),
            code_point_array(mv_code_point_array)
        {}
    };
    struct SequenceInfo {
        size_t elem_id_count;
        ValueID* elem_id_array;

        inline
        SequenceInfo(size_t elem_id_count, ValueID* mv_elem_id_array)
        :   elem_id_count{elem_id_count},
            elem_id_array{mv_elem_id_array}
        {}
    };

    struct Value {
        ValueKind kind;
        ValueInfo info;
    };

    static std::deque<ValueKind> s_value_kind_table;
    static std::deque<ValueInfo> s_value_info_table;
    static std::deque<std::string> s_value_serialized_string_table;
    static std::deque<size_t> s_value_serialized_string_hashes_table;
    static std::deque<StringInfo> s_value_string_info_table;
    static std::deque<SequenceInfo> s_value_tuple_info_table;

    // value creation:
    ValueID get_next_val_id() {
        assert(s_value_kind_table.size() == s_value_info_table.size());
        return s_value_kind_table.size();
    }
    void push_cached_serialized_data(ValueID val_id);

    ValueID push_val_u1(bool v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u1 = v;
        s_value_kind_table.push_back(ValueKind::U1);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_u8(uint8_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u8 = v;
        s_value_kind_table.push_back(ValueKind::U8);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_u16(uint16_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u16 = v;
        s_value_kind_table.push_back(ValueKind::U16);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_u32(uint32_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u32 = v;
        s_value_kind_table.push_back(ValueKind::U32);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_u64(uint64_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u64 = v;
        s_value_kind_table.push_back(ValueKind::U64);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_s8(int8_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s8 = v;
        s_value_kind_table.push_back(ValueKind::S8);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_s16(int16_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s16 = v;
        s_value_kind_table.push_back(ValueKind::S16);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_s32(int32_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s32 = v;
        s_value_kind_table.push_back(ValueKind::S32);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_s64(int64_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s64 = v;
        s_value_kind_table.push_back(ValueKind::S64);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_f32(float v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.f32 = v;
        s_value_kind_table.push_back(ValueKind::F32);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_f64(double v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.f64 = v;
        s_value_kind_table.push_back(ValueKind::F64);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValueID push_val_str(size_t code_point_count, int* mv_code_point_array) {
        auto id = get_next_val_id();

        auto string_info_index = s_value_string_info_table.size();
        s_value_string_info_table.emplace_back(
            code_point_count,
            mv_code_point_array
        );

        ValueInfo vi; vi.string_info_index = string_info_index;
        s_value_kind_table.push_back(ValueKind::S8);
        s_value_info_table.push_back(vi);

        push_cached_serialized_data(id);

        return id;
    }
    ValueID push_val_tuple(size_t elem_id_count, ValueID* mv_elem_id_array) {
        auto id = get_next_val_id();

        auto string_info_index = s_value_string_info_table.size();
        s_value_tuple_info_table.emplace_back(
            elem_id_count,
            mv_elem_id_array
        );

        ValueInfo vi; vi.string_info_index = string_info_index;
        s_value_kind_table.push_back(ValueKind::S8);
        s_value_info_table.push_back(vi);
        
        push_cached_serialized_data(id);

        return id;
    }

    // property accessors:
    ValueKind value_kind(ValueID value_id) {
        return s_value_kind_table[value_id];
    }
    ValueInfo value_info(ValueID value_id) {
        return s_value_info_table[value_id];
    }

    // serialization:
    size_t serialize_value(
        ValueID value_id,
        size_t max_out_size,
        char* out_array
    );
    size_t serialize_value_impl(
        ValueID value_id, 
        size_t max_out_size,
        char* out_array, 
        size_t* offset_p
    );
    size_t serialize_value(
        ValueID value_id,
        size_t max_out_size,
        char* out_array
    ) {
        size_t bytes_written_so_far = 0;
        return serialize_value_impl(
            value_id,
            max_out_size,
            out_array,
            &bytes_written_so_far
        );
    }
    size_t serialize_value_impl(
        ValueID value_id, 
        size_t max_out_size,
        char* out_array, 
        size_t* offset_p
    )
    {   
        ValueKind vk = value_kind(value_id);
        ValueInfo vi = value_info(value_id);

        switch (vk) {
            case ValueKind::U1: 
            {
                if (*offset_p + 1 >= max_out_size) {
                    return 0;
                }

                if (out_array) {
                    out_array[*offset_p++] = vi.u1;
                }

                return 1;
            } break;
            
            case ValueKind::U8: 
            case ValueKind::S8:
            {
                if (*offset_p + 1 >= max_out_size) {
                    return 0;
                }

                if (out_array) {
                    out_array[*offset_p++] = vi.u8;
                }

                return 1;
            } break;

            case ValueKind::U16: 
            case ValueKind::S16:
            {
                if (*offset_p + 2 >= max_out_size) {
                    return 0;
                }

                if (out_array) {
                    memcpy(
                        out_array + *offset_p,
                        &vi.u16,
                        sizeof(vi.u16)
                    );
                }
                *offset_p += sizeof(vi.u16);
                return sizeof(vi.u16);
            } break;
 
            case ValueKind::S32:
            case ValueKind::U32:
            case ValueKind::F32:
            {
                if (*offset_p + 4 >= max_out_size) {
                    return 0;
                }
                
                if (out_array) {
                    memcpy(
                        out_array + *offset_p,
                        &vi.u32,
                        sizeof(vi.u32)
                    );
                }
                *offset_p += sizeof(vi.u32);
                return sizeof(vi.u32);
            } break;

            case ValueKind::S64:
            case ValueKind::U64:
            case ValueKind::F64:
            {
                if (*offset_p + 8 >= max_out_size) {
                    return 0;
                }

                if (out_array) {
                    memcpy(
                        out_array + *offset_p,
                        &vi.u64,
                        sizeof(vi.u64)
                    );
                }
                *offset_p += sizeof(vi.u64);
                return sizeof(vi.u64);
            } break;

            case ValueKind::String:
            {
                // for strings, we write a length-prefixed array of code points
                StringInfo si = s_value_string_info_table[vi.string_info_index];
                size_t const bytes_per_code_point = sizeof(int);
                size_t const bytes_written = (
                    // length prefix
                    sizeof(size_t) +

                    // code points:
                    si.code_point_count * bytes_per_code_point
                );

                if (*offset_p + bytes_written >= max_out_size) {
                    return 0;
                }

                for (size_t i = 0; i < si.code_point_count; i++) {
                    int code_point = si.code_point_array[i];
                    if (out_array) {
                        memcpy(
                            out_array + *offset_p,
                            &code_point,
                            sizeof(code_point)
                        );
                    }
                    *offset_p += sizeof(code_point);
                }

                return bytes_written;
            } break;

            case ValueKind::Tuple:
            case ValueKind::Array:
            case ValueKind::Slice:
            {
                // for sequences, we recursively serialize each field.
                SequenceInfo ti = s_value_tuple_info_table[
                    vi.sequence_info_index
                ];
                size_t written_byte_count = 0;
                for (size_t i_elem = 0; i_elem < ti.elem_id_count; i_elem++) {
                    size_t copied_size = *offset_p;
                    size_t field_byte_count = serialize_value_impl(
                        ti.elem_id_array[i_elem],
                        max_out_size,
                        nullptr,
                        &copied_size
                    );
                    if (written_byte_count + field_byte_count > max_out_size) {
                        return written_byte_count;
                    } else {
                        written_byte_count += serialize_value_impl(
                            ti.elem_id_array[i_elem],
                            max_out_size,
                            out_array,
                            offset_p
                        );
                    }
                }
                return written_byte_count;
            } break;
            default: {
                throw new Panic("Unknown ValueKind");
            }
        }
    }
    void push_cached_serialized_data(ValueID val_id) {
        static thread_local char ser_buffer[MAX_VAL_HASH_BYTE_COUNT];
        static auto const hash_callable = std::hash<std::string>();
        
        size_t ser_buffer_byte_count = serialize_value(
            val_id, 
            MAX_VAL_HASH_BYTE_COUNT, 
            ser_buffer
        );
        std::string serialized_string{
            ser_buffer,
            ser_buffer_byte_count
        };

        size_t serialized_string_hash = hash_callable(serialized_string);

        s_value_serialized_string_table.push_back(
            serialized_string
        );
        s_value_serialized_string_hashes_table.push_back(
            serialized_string_hash
        );
    }

    // equality checks:
    bool equals(ValueID v1, ValueID v2) {
        if (v1 == v2) {
            return true;
        }

        auto const kind1 = s_value_kind_table[v1];
        auto const kind2 = s_value_kind_table[v2];
        if (kind1 != kind2) {
            return false;
        }
        auto const kind = kind1;
        
        switch (kind) {
            case ValueKind::Unit: {
                return true;
            }

            case ValueKind::U1: 
            {
                return (
                    s_value_info_table[v1].u1 ==
                    s_value_info_table[v2].u1
                );
            } break;
            
            case ValueKind::S8:
            case ValueKind::U8: 
            {
                return (
                    s_value_info_table[v1].u8 ==
                    s_value_info_table[v2].u8
                );
            } break;
            
            case ValueKind::S16:
            case ValueKind::U16:
            {
                return (
                    s_value_info_table[v1].u16 ==
                    s_value_info_table[v2].u16
                );
            } break;
            
            case ValueKind::S32:
            case ValueKind::U32:
            case ValueKind::F32:
            {
                return (
                    s_value_info_table[v1].u32 ==
                    s_value_info_table[v2].u32
                );
            } break;
            
            case ValueKind::S64:
            case ValueKind::U64:
            case ValueKind::F64:
            {
                return (
                    s_value_info_table[v1].u64 ==
                    s_value_info_table[v2].u64
                );
            } break;

            case ValueKind::Tuple:
            case ValueKind::Array:
            case ValueKind::Slice:
            default:
            {
                auto const hash1 = s_value_serialized_string_hashes_table[v1];
                auto const hash2 = s_value_serialized_string_hashes_table[v2];
                if (hash1 != hash2) {
                    return false;
                }
                return (
                    s_value_serialized_string_table[v1] ==
                    s_value_serialized_string_table[v2]
                );
            }   
        }
    }

}