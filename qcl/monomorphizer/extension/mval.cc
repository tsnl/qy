#include "mval.hh"

#include <deque>
#include <string>
#include <vector>
#include <cstddef>
#include <cstdint>
#include <cassert>

#include "id-intern.hh"
#include "id-mast.hh"
#include "panic.hh"

namespace monomorphizer::mval {

    extern size_t const MAX_VAL_HASH_BYTE_COUNT = 64 * 1024;
    extern ValVarID const NULL_VID = -1;
    
    static ValVarID s_unit_val_id = NULL_VID;

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
        ValVarID* elem_id_array;

        inline
        SequenceInfo(size_t elem_id_count, ValVarID* mv_elem_id_array)
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
    static std::deque<SequenceInfo> s_value_sequence_info_table;
    static std::deque<FuncInfo> s_func_info_table;

    // value creation:
    ValVarID get_next_val_id() {
        assert(s_value_kind_table.size() == s_value_info_table.size());
        return s_value_kind_table.size();
    }
    void push_cached_serialized_data(ValVarID val_id);

    ValVarID push_unit() {
        auto id = get_next_val_id();
        s_value_kind_table.push_back(VK_UNIT);
        s_value_info_table.emplace_back();
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID get_unit() {
        if (s_unit_val_id == NULL_VID) {
            s_unit_val_id = push_unit();
            assert(s_unit_val_id != NULL_VID);
        }
        return s_unit_val_id;
    }
    ValVarID push_u1(bool v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u1 = v;
        s_value_kind_table.push_back(VK_U1);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_u8(uint8_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u8 = v;
        s_value_kind_table.push_back(VK_U8);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_u16(uint16_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u16 = v;
        s_value_kind_table.push_back(VK_U16);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_u32(uint32_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u32 = v;
        s_value_kind_table.push_back(VK_U32);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_u64(uint64_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u64 = v;
        s_value_kind_table.push_back(VK_U64);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_s8(int8_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s8 = v;
        s_value_kind_table.push_back(VK_S8);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_s16(int16_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s16 = v;
        s_value_kind_table.push_back(VK_S16);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_s32(int32_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s32 = v;
        s_value_kind_table.push_back(VK_S32);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_s64(int64_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s64 = v;
        s_value_kind_table.push_back(VK_S64);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_f32(float v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.f32 = v;
        s_value_kind_table.push_back(VK_F32);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_f64(double v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.f64 = v;
        s_value_kind_table.push_back(VK_F64);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);
        return id;
    }
    ValVarID push_str(size_t code_point_count, int* mv_code_point_array) {
        auto id = get_next_val_id();

        auto string_info_index = s_value_string_info_table.size();
        s_value_string_info_table.emplace_back(
            code_point_count,
            mv_code_point_array
        );

        ValueInfo vi; vi.string_info_index = string_info_index;
        s_value_kind_table.push_back(VK_S8);
        s_value_info_table.push_back(vi);

        push_cached_serialized_data(id);

        return id;
    }
    ValVarID push_tuple(size_t elem_id_count, ValVarID* mv_elem_id_array) {
        auto id = get_next_val_id();

        auto sequence_info_index = s_value_sequence_info_table.size();
        s_value_sequence_info_table.emplace_back(
            elem_id_count,
            mv_elem_id_array
        );

        ValueInfo vi; vi.sequence_info_index = sequence_info_index;
        
        s_value_kind_table.push_back(VK_TUPLE);
        s_value_info_table.push_back(vi);
        push_cached_serialized_data(id);

        return id;
    }
    ValVarID push_function(
        uint32_t arg_name_count,
        intern::IntStr* mv_arg_name_array,
        uint32_t ctx_enclosed_id_count,
        CtxEnclosedId* mv_ctx_enclosed_id_array,
        mast::ExpID body_exp_id
    ) {
        auto id = get_next_val_id();

        auto function_info_index = s_func_info_table.size();
        s_func_info_table.emplace_back(
            arg_name_count,
            ctx_enclosed_id_count,
            mv_arg_name_array,
            mv_ctx_enclosed_id_array,
            body_exp_id
        );

        ValueInfo vi; vi.func_info_index = function_info_index;
        s_value_kind_table.push_back(VK_FUNCTION);
        s_value_info_table.push_back(vi);

        push_cached_serialized_data(id);

        return id;
    }

    // property accessors:
    ValueKind value_kind(ValVarID value_id) {
        return s_value_kind_table[value_id];
    }
    ValueInfo value_info(ValVarID value_id) {
        return s_value_info_table[value_id];
    }
    size_t get_seq_count(size_t sequence_info_index) {
        return s_value_sequence_info_table[sequence_info_index].elem_id_count;
    }
    std::optional<ValVarID> get_seq_elem(ValVarID tuple_val_id, size_t elem_index) {
        size_t sequence_info_index = s_value_info_table[tuple_val_id].sequence_info_index;
        SequenceInfo elem_info = s_value_sequence_info_table[sequence_info_index];
        ValVarID* elem_array = elem_info.elem_id_array;
        size_t elem_count = elem_info.elem_id_count;
        if (elem_index < elem_count) {
            return elem_array[elem_index];
        } else {
            return {};
        }
    }
    FuncInfo* get_func_info(size_t func_info_index) {
        return &s_func_info_table[func_info_index];
    }

    // serialization:
    size_t serialize_value(
        ValVarID value_id,
        size_t max_out_size,
        char* out_array
    );
    size_t serialize_value_impl(
        ValVarID value_id, 
        size_t max_out_size,
        char* out_array, 
        size_t* offset_p
    );
    size_t serialize_value(
        ValVarID value_id,
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
        ValVarID value_id, 
        size_t max_out_size,
        char* out_array, 
        size_t* offset_p
    )
    {   
        ValueKind vk = value_kind(value_id);
        ValueInfo vi = value_info(value_id);

        switch (vk) {
            // no serialization: only ID equality required:
            case VK_UNIT:
            case VK_FUNCTION:
            {
                return 0;
            }

            case VK_U1: 
            {
                if (*offset_p + 1 >= max_out_size) {
                    return 0;
                }

                if (out_array) {
                    out_array[*offset_p++] = vi.u1;
                }

                return 1;
            } break;
            
            case VK_U8: 
            case VK_S8:
            {
                if (*offset_p + 1 >= max_out_size) {
                    return 0;
                }

                if (out_array) {
                    out_array[*offset_p++] = vi.u8;
                }

                return 1;
            } break;

            case VK_U16: 
            case VK_S16:
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
 
            case VK_S32:
            case VK_U32:
            case VK_F32:
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

            case VK_S64:
            case VK_U64:
            case VK_F64:
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

            case VK_STRING:
            {
                // for strings, we write a length-prefixed array of code points
                StringInfo si = s_value_string_info_table[vi.string_info_index];
                size_t const bytes_per_code_point = sizeof(int);
                size_t const bytes_written = (
                    sizeof(size_t) +                                // length prefix
                    si.code_point_count * bytes_per_code_point      // si.code_point_count code points
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

            case VK_TUPLE:
            case VK_ARRAY:
            case VK_SLICE:
            {
                // for sequences, we recursively serialize each field.
                SequenceInfo ti = s_value_sequence_info_table[vi.sequence_info_index];
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
    void push_cached_serialized_data(ValVarID val_id) {
        static thread_local char ser_buffer[MAX_VAL_HASH_BYTE_COUNT];
        static auto const hash_callable = std::hash<std::string>();
        
        size_t ser_buffer_byte_count = serialize_value(
            val_id, 
            MAX_VAL_HASH_BYTE_COUNT, 
            ser_buffer
        );
        
        std::string serialized_string;
        size_t serialized_string_hash;
        if (ser_buffer_byte_count == 0) {
            // 0-length data <=> empty serialization data.
            serialized_string = "";
            serialized_string_hash = 0;
        } else {
            serialized_string = std::string{
                ser_buffer,
                ser_buffer_byte_count
            };
            serialized_string_hash = hash_callable(serialized_string);
        }
        
        s_value_serialized_string_table.push_back(serialized_string);
        s_value_serialized_string_hashes_table.push_back(serialized_string_hash);
    }

    // equality checks:
    bool equals(ValVarID v1, ValVarID v2) {
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
            case VK_UNIT: {
                throw new Panic("Unit value is not unique! ValVarIDs not equal, but same kind");
            }
            case VK_FUNCTION: {
                // unless function IDs are equal, return 'false':
                return false;
            }

            case VK_U1: 
            {
                return (
                    s_value_info_table[v1].u1 ==
                    s_value_info_table[v2].u1
                );
            } break;
            
            case VK_S8:
            case VK_U8: 
            {
                return (
                    s_value_info_table[v1].u8 ==
                    s_value_info_table[v2].u8
                );
            } break;
            
            case VK_S16:
            case VK_U16:
            {
                return (
                    s_value_info_table[v1].u16 ==
                    s_value_info_table[v2].u16
                );
            } break;
            
            case VK_S32:
            case VK_U32:
            case VK_F32:
            {
                return (
                    s_value_info_table[v1].u32 ==
                    s_value_info_table[v2].u32
                );
            } break;
            
            case VK_S64:
            case VK_U64:
            case VK_F64:
            {
                return (
                    s_value_info_table[v1].u64 ==
                    s_value_info_table[v2].u64
                );
            } break;

            case VK_TUPLE:
            case VK_ARRAY:
            case VK_SLICE:
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
