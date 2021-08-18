#include "gdef.hh"

#include <vector>
#include <deque>
#include <string>

#include "shared-enums.hh"
#include "id-gdef.hh"
#include "id-mast.hh"
#include "mast.hh"
#include "panic.hh"

namespace monomorphizer::gdef {

    // Constants:
    extern GDefID const NULL_GDEF_ID = UNIVERSAL_NULL_ID;

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
        char* def_name;
        size_t opt_target_id;

        inline DefInfo(char* mv_def_name)
        :   def_name(mv_def_name),
            opt_target_id(NULL_GDEF_ID)
        {}

        inline DefInfo(char* mv_def_name, size_t target_id)
        :   def_name(mv_def_name),
            opt_target_id(target_id)
        {}
    };

    //
    // Constructors:
    //

    GDefID declare_global_def(DefKind kind, char* mv_def_name) {
        bool kind_is_const_not_bv = (
            kind != DefKind::BV_EXP &&
            kind != DefKind::BV_TS
        );

        size_t pa_size = s_def_kind_table.size();
        assert(
            pa_size == s_def_info_table.size() &&
            "Parallel arrays out of sync"
        );
        size_t def_id = s_def_kind_table.size();
        size_t target_id = UNIVERSAL_NULL_ID;
        
        s_def_kind_table.push_back(kind);
        s_def_info_table.emplace_back(mv_def_name, target_id);
        s_def_is_const_not_var_table.push_back(kind_is_const_not_bv);
        
        return def_id;
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
    void set_def_target(GDefID def_id, size_t target_id) {
        assert(target_id != UNIVERSAL_NULL_ID);
        s_def_info_table[def_id].opt_target_id = target_id;
    }
    size_t get_def_target(GDefID def_id) {
        return s_def_info_table[def_id].opt_target_id;
    }

}
