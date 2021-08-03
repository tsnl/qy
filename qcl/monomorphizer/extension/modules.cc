#include "modules.hh"

#include <vector>
#include <deque>
#include <string>
#include <cstdint>
#include <cassert>

#include "mast.hh"
#include "defs.hh"

//
// Implementation: Compile-time constants
//

namespace monomorphizer::modules {
    extern MonoModID const NULL_MONO_TEMPLATE_ID = -1;
    extern PolyModID const NULL_POLY_TEMPLATE_ID = -1;
}

//
// Implementation: values
// NOTE: values are serializable intermediates used for computation.
// NOTE: serialization => easy hashing
// NOTE: ValueID is NOT unique to each value!!
//  - vid1 = vid2 => vid1 == vid2   (by identity)
//  - vid1 != vid2 =/=> vid1 !== vid2   (diff identity may still be equal)
//

namespace monomorphizer::modules {

    using ValueID = size_t;

    enum class ValueKind {
        Unit,
        U1, U8, U16, U32, U64,
        S8, S16, S32, S64,
        F32, F64,
        String,
        Tuple
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
        size_t tuple_info_index;
    };

    struct StringInfo {
        size_t code_point_count;
        int* code_point_array;

        inline
        StringInfo(size_t code_point_count, int* mv_code_point_array)
        :   code_point_count(code_point_count),
            code_point_array(mv_code_point_array)
        {}
    };
    struct TupleInfo {
        size_t elem_id_count;
        ValueID* elem_id_array;

        inline
        TupleInfo(size_t elem_id_count, ValueID* mv_elem_id_array)
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
    static std::deque<StringInfo> s_value_string_info_table;
    static std::deque<TupleInfo> s_value_tuple_info_table;

    // value creation:
    ValueID get_next_val_id() {
        assert(s_value_kind_table.size() == s_value_info_table.size());
        return s_value_kind_table.size();
    }
    ValueID push_val_u1(bool v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u1 = v;
        s_value_kind_table.push_back(ValueKind::U1);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_u8(uint8_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u8 = v;
        s_value_kind_table.push_back(ValueKind::U8);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_u16(uint16_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u16 = v;
        s_value_kind_table.push_back(ValueKind::U16);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_u32(uint32_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u32 = v;
        s_value_kind_table.push_back(ValueKind::U32);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_u64(uint64_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.u64 = v;
        s_value_kind_table.push_back(ValueKind::U64);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_s8(int8_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s8 = v;
        s_value_kind_table.push_back(ValueKind::S8);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_s16(int16_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s16 = v;
        s_value_kind_table.push_back(ValueKind::S16);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_s32(int32_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s32 = v;
        s_value_kind_table.push_back(ValueKind::S32);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_s64(int64_t v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.s64 = v;
        s_value_kind_table.push_back(ValueKind::S64);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_f32(float v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.f32 = v;
        s_value_kind_table.push_back(ValueKind::F32);
        s_value_info_table.push_back(vi);
        return id;
    }
    ValueID push_val_f64(double v) {
        auto id = get_next_val_id();
        ValueInfo vi; vi.f64 = v;
        s_value_kind_table.push_back(ValueKind::F64);
        s_value_info_table.push_back(vi);
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
    // TODO: write a method that recursively emits a byte-sequence that we can
    //       run a string hash function on.
}

//
// Implementation: arg-list tries:
//

namespace monomorphizer::modules {

    using TrieNodeID = size_t;
    using ArgListID = TrieNodeID;

    struct TrieNode;
    struct TrieEdge;

    struct TrieNode {
        std::vector<TrieEdge> m_edges;    
    };
    // struct TrieEdge {
    //     ValueID value;
    //     TrieNodeID next;
    // };

    // TODO: need a way to ID values uniquely/hash them into keys (cf above)
    // TODO: need to pass TID to MAST type-specifiers
    //   - guaranteed to be unique by typer
    //   - can use these TIDs as keys

    // ONCE we have a serializable `Value` format and a `TID`, we can use a 
    // hash-map to build a trie.

    // Then, each Trie node represents a unique, non-negative list of args.

}

//
// Implementation: module data storage
//

namespace monomorphizer::modules {

    struct CommonModInfo32 {
        std::vector<mast::NameNodeRelation> fields;
        char* name;
    };

    struct MonoModInfo {
        PolyModID opt_parent_mod_id;
    };

    struct PolyModInfo {
        size_t bv_count;
        DefID* bv_def_id_array;
    };

    static std::vector<CommonModInfo32> s_mono_common_info_table;
    static std::vector<MonoModInfo> s_mono_mod_info_table;

    static std::vector<CommonModInfo32> s_poly_common_info_table;
    static std::vector<PolyModInfo> s_poly_custom_info_table;
}

//
// Implementation: lazily getting MonoModID from PolyModID
//

//
// Interface: Construction
//

namespace monomorphizer::modules {

    void ensure_init() {
        mast::ensure_init();
        defs::ensure_init();
    }
    void drop() {
        mast::drop();
        defs::drop();
    }

    // Monomorphic template construction:
    MonoModID new_monomorphic_template(
        char* mv_name,
        PolyModID opt_parent_mod_id
    ) {
        MonoModID id = s_mono_mod_info_table.size();
        s_mono_common_info_table.push_back({{}, mv_name});
        s_mono_mod_info_table.push_back({opt_parent_mod_id});
        return id;
    }
    void add_mono_template_ts_field(
        MonoModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        TypeSpecID bound_ts_id
    ) {
        s_mono_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_ts_id
        });
    }
    void add_mono_template_exp_field(
        MonoModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        ExpID bound_exp_id
    ) {
        s_mono_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_exp_id
        });
    }

    // Polymorphic template construction:
    PolyModID new_polymorphic_template(
        char* mv_template_name,
        size_t bv_def_id_count,
        DefID* mv_bv_def_id_array
    ) {
        PolyModID id = s_poly_custom_info_table.size();
        s_poly_common_info_table.push_back({{}, mv_template_name});
        s_poly_custom_info_table.push_back(
            {bv_def_id_count, mv_bv_def_id_array}
        );
        return id;
    }
    void add_poly_template_ts_field(
        PolyModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        TypeSpecID bound_ts_id
    ) {
        s_poly_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_ts_id
        });
    }
    void add_poly_template_exp_field(
        PolyModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        ExpID bound_exp_id
    ) {
        s_poly_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_exp_id
        });
    }

}

//
// Interface: monomorphize sub-graph
//

namespace monomorphizer::modules {

    void monomorphize_subgraph(MonoModID first_mono_template_id) {
        // todo: scan for GetFieldInPolyMod, get monomorph, and execute
    }

}