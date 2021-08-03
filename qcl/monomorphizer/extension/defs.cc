#include "defs.hh"

#include <vector>

#include "id-defs.hh"

namespace monomorphizer::defs {

    // Constants:
    extern DefID const NULL_DEF_ID = -1;

    // Definitions are stored in 2 different-sized tables.
    // We store a common table of kinds and indices into respective lists.
    struct ConstDefInfo;
    struct VarDefInfo;

    static bool s_is_already_init = false;
    static std::vector<bool> s_def_is_const_not_var_table;
    static std::vector<DefKind> s_def_kind_table;
    static std::vector<size_t> s_def_index_table;
    static std::vector<ConstDefInfo> s_const_def_info_table;
    static std::vector<VarDefInfo> s_var_def_info_table;

    void ensure_init() {
        if (!s_is_already_init) {
            size_t init_def_capacity = 16 * 1024;

            s_def_is_const_not_var_table.reserve(init_def_capacity);
            s_def_kind_table.reserve(init_def_capacity);
            s_def_index_table.reserve(init_def_capacity);
            
            // reserving against the worst-case: all constants or variables
            s_const_def_info_table.reserve(init_def_capacity);
            s_var_def_info_table.reserve(init_def_capacity);

            s_is_already_init = true;
        }
    }

    void drop() {
        if (s_is_already_init) {
            s_def_is_const_not_var_table.clear();
            s_def_kind_table.clear();
            s_def_index_table.clear();
            s_const_def_info_table.clear();
            s_var_def_info_table.clear();
            s_is_already_init = false;
        }
    }

    //
    // Const definitions:
    //

    struct ConstDefInfo {

    };

    //
    // Bound Variable definitions:
    //

    struct VarDefInfo {

    };

    DefID define_const(
        char const* mod_name,
        char const* def_name,
        NodeID node_id,
        bool is_global
    ) {
        return 0;
    }

    DefID define_bound_var_ts(
        char const* mod_name,
        char const* formal_var_name
    ) {
        return NULL_DEF_ID;
    }

    DefID define_bound_var_exp(
        char const* mod_name,
        char const* formal_var_name
    ) {
        // todo: implement me!
    }

    // query definition info:
    bool get_def_is_bv(DefID def_id) {
        return !s_def_is_const_not_var_table[def_id];
    }
    DefKind get_def_kind(DefID def_id) {
        return s_def_kind_table[def_id];
    }

}