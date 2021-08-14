#include "gdef.hh"

#include <vector>
#include <deque>
#include <string>

#include "id-gdef.hh"
#include "id-mast.hh"
#include "mast.hh"
#include "panic.hh"

namespace monomorphizer::gdef {

    // Constants:
    extern GDefID const NULL_GDEF_ID = -1;

    struct DefInfo;
    
    // Pre-reserved vectors => stable slabs of memory (for AoS pattern)
    static bool s_is_already_init = false;
    static std::vector<bool> s_def_is_const_not_var_table;
    static std::vector<DefKind> s_def_kind_table;
    static std::vector<DefInfo> s_def_info_table;
    // static std::vector<VarDefInfo> s_var_def_info_table;
    
    void ensure_defs_init() {
        if (!s_is_already_init) {
            size_t init_def_capacity = 16 * 1024;

            // reserving vectors:
            s_def_is_const_not_var_table.reserve(init_def_capacity);
            s_def_kind_table.reserve(init_def_capacity);
            s_def_info_table.reserve(init_def_capacity);
            
            // finally, marking `init` as complete:
            s_is_already_init = true;
        }
    }

    void drop_defs() {
        if (s_is_already_init) {
            s_def_is_const_not_var_table.clear();
            s_def_kind_table.clear();
            s_def_info_table.clear();
            s_is_already_init = false;
        }
    }

    //
    // DefInfo:
    //

    struct DefInfo {
        char* const def_name;
        size_t opt_target_id;

        inline DefInfo(char* mv_def_name)
        :   def_name(mv_def_name),
            opt_target_id()
        {}

        inline DefInfo(char* mv_def_name, size_t target_id)
        :   def_name(mv_def_name),
            opt_target_id(target_id)
        {}
    };

    //
    // Constructors:
    //

    GDefID help_emplace_common_def_info(
        DefKind kind,
        char* mv_def_name,
        size_t target_id,
        bool kind_is_const_not_bv
    ) {
        size_t pa_size = s_def_kind_table.size();
        assert(
            pa_size == s_def_info_table.size() &&
            "Parallel arrays out of sync"
        );
        size_t def_id = s_def_kind_table.size();
        
        s_def_kind_table.push_back(kind);
        s_def_info_table.emplace_back(mv_def_name, target_id);
        s_def_is_const_not_var_table.push_back(kind_is_const_not_bv);
        
        return def_id;
    }

    GDefID help_emplace_const_mast_def(char* mv_def_name, bool is_t_not_v) {
        bool bound_node_id_is_exp_not_ts = !is_t_not_v;
        DefKind def_kind = (
            bound_node_id_is_exp_not_ts ?
                DefKind::CONST_EXP :
                DefKind::CONST_TS
        );
        return help_emplace_common_def_info(
            def_kind,
            mv_def_name,
            mast::NULL_NODE_ID,
            true
        );
    }

    GDefID help_emplace_tot_const_def(
        DefKind def_kind,
        char* mv_def_name,
        size_t bound_id
    ) {
        return help_emplace_common_def_info(
            def_kind,
            mv_def_name,
            bound_id,
            true
        );
    }

    GDefID help_emplace_bv(
        DefKind def_kind,
        char* mv_def_name
    ) {
        return help_emplace_common_def_info(
            def_kind,
            mv_def_name,
            -1,  // doesn't matter
            false
        );
    }

    GDefID declare_t_const_mast_node(char* mv_def_name) {
        return help_emplace_const_mast_def(mv_def_name, false);
    }
    GDefID declare_v_const_mast_node(char* mv_def_name) {
        return help_emplace_const_mast_def(mv_def_name, true);
    }

    GDefID define_total_const_value(
        char* mv_def_name,
        mval::ValueID value_id
    ) {
        return help_emplace_tot_const_def(
            DefKind::CONST_TOT_VAL,
            mv_def_name,
            value_id
        );
    }

    GDefID define_total_const_type(
        char* mv_def_name,
        mtype::TID type_id
    ) {
        return help_emplace_tot_const_def(
            DefKind::CONST_TOT_TID,
            mv_def_name,
            type_id
        );
    }

    void define_declared_t_const(GDefID declared_def_id, mast::TypeSpecID ts_id) {
        auto info = &s_def_info_table[declared_def_id];
        assert(info->opt_target_id == mast::NULL_NODE_ID);
        info->opt_target_id = ts_id;
    }

    void define_declared_v_const(GDefID declared_def_id, mast::ExpID exp_id) {
        auto info = &s_def_info_table[declared_def_id];
        assert(info->opt_target_id == mast::NULL_NODE_ID);
        info->opt_target_id = exp_id;
    }

    GDefID define_bound_var_ts(
        char* mv_formal_var_name
    ) {
        return help_emplace_bv(
            DefKind::BV_TS,
            mv_formal_var_name
        );
    }

    GDefID define_bound_var_exp(
        char* mv_formal_var_name
    ) {
        return help_emplace_bv(
            DefKind::BV_EXP,
            mv_formal_var_name
        );
    }

    // query definition info:
    bool get_def_is_bv(GDefID def_id) {
        return !s_def_is_const_not_var_table[def_id];
    }
    DefKind get_def_kind(GDefID def_id) {
        return s_def_kind_table[def_id];
    }
    char const* get_def_name(GDefID def_id) {
        return s_def_info_table[def_id].def_name;
    }
    void store_id_at_def_id(GDefID def_id, size_t v) {
        s_def_info_table[def_id].opt_target_id = v;
    }
    size_t load_id_from_def_id(GDefID def_id) {
        return s_def_info_table[def_id].opt_target_id;
    }

}