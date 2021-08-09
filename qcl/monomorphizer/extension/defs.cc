#include "defs.hh"

#include <vector>
#include <deque>
#include <string>

#include "id-defs.hh"
#include "id-mast.hh"
#include "mast.hh"
#include "panic.hh"

namespace monomorphizer::defs {

    // Constants:
    extern DefID const NULL_DEF_ID = -1;

    // Definitions are stored in 2 different-sized tables.
    // We store a common table of kinds and indices into respective lists.
    struct CommonDefInfo;
    struct ConstDefInfo;
    struct VarDefInfo;

    // Pre-reserved vectors => stable slabs of memory (for AoS pattern)
    static bool s_is_already_init = false;
    static std::vector<bool> s_def_is_const_not_var_table;
    static std::vector<bool> s_def_is_global_table;
    static std::vector<DefKind> s_def_kind_table;
    static std::vector<CommonDefInfo> s_def_common_info_table;
    static std::vector<ConstDefInfo> s_const_mast_def_info_table;
    static std::vector<ConstDefInfo> s_tot_const_def_info;
    // static std::vector<VarDefInfo> s_var_def_info_table;
    
    void ensure_init() {
        if (!s_is_already_init) {
            size_t init_def_capacity = 16 * 1024;

            // reserving vectors:
            s_def_is_const_not_var_table.reserve(init_def_capacity);
            s_def_is_global_table.resize(init_def_capacity);
            s_def_kind_table.reserve(init_def_capacity);
            s_def_common_info_table.reserve(init_def_capacity);
            // reserving against the worst-case: all of one kind:
            s_const_mast_def_info_table.reserve(init_def_capacity);
            s_tot_const_def_info.reserve(init_def_capacity);
            // s_var_def_info_table.reserve(init_def_capacity);

            // finally, marking `init` as complete:
            s_is_already_init = true;
        }
    }

    void drop() {
        if (s_is_already_init) {
            s_def_is_const_not_var_table.clear();
            s_def_is_global_table.clear();
            s_def_kind_table.clear();
            s_def_common_info_table.clear();
            s_const_mast_def_info_table.clear();
            s_tot_const_def_info.clear();
            // s_var_def_info_table.clear();
            s_is_already_init = false;
        }
    }

    //
    // CommonInfo:
    //

    struct CommonDefInfo {
        char* const def_name;
        size_t const info_index;

        inline
        CommonDefInfo(char* mv_def_name, size_t init_info_index)
        :   def_name(mv_def_name),
            info_index(init_info_index)
        {}
    };

    //
    // Const definitions:
    //

    struct ConstDefInfo {
        size_t const target_id;

        inline
        ConstDefInfo(size_t init_target_id)
        : target_id(init_target_id)
        {}
    };

    //
    // Bound Variable definitions:
    //

    // struct VarDefInfo {
    //     // it seems like this space is not required
    //     int dummy;
    // };

    //
    // Constructor helpers:
    //

    bool is_mast_node_exp_not_ts(mast::NodeID node_id) {
        mast::NodeKind nk = mast::get_node_kind(node_id);
        switch (nk) {
            // type specs:
            case mast::NodeKind::TS_UNIT:
            case mast::NodeKind::TS_ID:
            case mast::NodeKind::TS_PTR:
            case mast::NodeKind::TS_ARRAY:
            case mast::NodeKind::TS_SLICE:
            case mast::NodeKind::TS_FUNC_SGN:
            case mast::NodeKind::TS_TUPLE:
            case mast::NodeKind::TS_GET_POLY_MODULE_FIELD:
            case mast::NodeKind::TS_GET_MONO_MODULE_FIELD: {
                return false;
            } break;
            
            // expressions:
            case mast::NodeKind::EXP_UNIT:
            case mast::NodeKind::EXP_INT:
            case mast::NodeKind::EXP_FLOAT:
            case mast::NodeKind::EXP_STRING:
            case mast::NodeKind::EXP_ID:
            case mast::NodeKind::EXP_FUNC_CALL:
            case mast::NodeKind::EXP_UNARY_OP:
            case mast::NodeKind::EXP_BINARY_OP:
            case mast::NodeKind::EXP_IF_THEN_ELSE:
            case mast::NodeKind::EXP_GET_TUPLE_FIELD:
            case mast::NodeKind::EXP_GET_POLY_MODULE_FIELD:
            case mast::NodeKind::EXP_GET_MONO_MODULE_FIELD:
            case mast::NodeKind::EXP_LAMBDA:
            case mast::NodeKind::EXP_ALLOCATE_ONE:
            case mast::NodeKind::EXP_ALLOCATE_MANY:
            case mast::NodeKind::EXP_CHAIN: {
                return true;
            }

            // otherwise, error
            default: {
                throw new Panic(
                    "Tried binding invalid AST node kind: "
                    "expected TypeSpec or Exp only"
                );
            }
        }
    }

    //
    // Constructors:
    //

    DefID help_emplace_common_def_info(
        DefKind kind,
        char* mv_def_name,
        size_t info_index,
        bool is_global,
        bool kind_is_const_not_bv
    ) {
        size_t pa_size = s_def_kind_table.size();
        assert(
            pa_size == s_def_common_info_table.size() &&
            pa_size == s_def_is_global_table.size() &&
            pa_size == s_def_is_const_not_var_table.size() &&
            "Parallel arrays out of sync"
        );
        size_t def_id = s_def_kind_table.size();
        
        s_def_kind_table.push_back(kind);
        s_def_common_info_table.emplace_back(mv_def_name, info_index);
        s_def_is_global_table.push_back(is_global);
        s_def_is_const_not_var_table.push_back(kind_is_const_not_bv);
        
        return def_id;
    }

    DefID help_emplace_const_mast_def(
        char* mv_def_name,
        mast::NodeID node_id,
        bool is_global
    ) {
        bool bound_node_id_is_exp_not_ts = is_mast_node_exp_not_ts(node_id);
        DefKind def_kind = (
            bound_node_id_is_exp_not_ts ?
                DefKind::CONST_EXP :
                DefKind::CONST_TS
        );

        size_t target_id = node_id;
        size_t info_index = s_const_mast_def_info_table.size();
        s_const_mast_def_info_table.emplace_back(target_id);

        return help_emplace_common_def_info(
            def_kind,
            mv_def_name,
            info_index,
            is_global,
            true
        );
    }

    DefID help_emplace_tot_const_def(
        DefKind def_kind,
        char* mv_def_name,
        size_t bound_id,
        bool is_global
    ) {
        size_t info_index = s_const_mast_def_info_table.size();
        s_const_mast_def_info_table.emplace_back(bound_id);

        return help_emplace_common_def_info(
            def_kind,
            mv_def_name,
            info_index,
            is_global,
            true
        );
    }

    DefID help_emplace_bv(
        DefKind def_kind,
        char* mv_def_name
    ) {
        return help_emplace_common_def_info(
            def_kind,
            mv_def_name,
            0,
            true,
            false
        );
    }

    DefID define_const_mast_node(
        char* mv_def_name,
        mast::NodeID node_id,
        bool is_global
    ) {
        return help_emplace_const_mast_def(
            mv_def_name,
            node_id,
            is_global
        );
    }

    DefID define_total_const_value(
        char* mv_def_name,
        mval::ValueID value_id,
        bool is_global
    ) {
        return help_emplace_tot_const_def(
            DefKind::CONST_TOT_VAL,
            mv_def_name,
            value_id,
            is_global
        );
    }

    DefID define_total_const_type(
        char* mv_def_name,
        mtype::MTypeID type_id,
        bool is_global
    ) {
        return help_emplace_tot_const_def(
            DefKind::CONST_TOT_TID,
            mv_def_name,
            type_id,
            is_global
        );
    }

    DefID define_bound_var_ts(
        char* mv_formal_var_name
    ) {
        return help_emplace_bv(
            DefKind::BV_TS,
            mv_formal_var_name
        );
    }

    DefID define_bound_var_exp(
        char* mv_formal_var_name
    ) {
        return help_emplace_bv(
            DefKind::BV_EXP,
            mv_formal_var_name
        );
    }

    // query definition info:
    bool get_def_is_bv(DefID def_id) {
        return !s_def_is_const_not_var_table[def_id];
    }
    DefKind get_def_kind(DefID def_id) {
        return s_def_kind_table[def_id];
    }
    char const* get_mod_name(DefID def_id) {
        return s_def_common_info_table[def_id].def_name;
    }
    char const* get_def_name(DefID def_id) {
        return s_def_common_info_table[def_id].def_name;
    }

}