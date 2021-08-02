#include "defs.hh"

#include <vector>

namespace defs {

    // Definitions are stored in 2 different-sized tables.
    // We store a common table of kinds and indices into respective lists.
    struct ConstDefInfo;
    struct VarDefInfo;

    static std::vector<bool> s_def_is_const_not_var_table;
    static std::vector<DefKind> s_def_kind_table;
    static std::vector<size_t> s_def_index_table;
    static std::vector<ConstDefInfo> s_const_def_info_table;
    static std::vector<VarDefInfo> s_var_def_info_table;

    void init(size_t init_def_capacity) {
        s_def_is_const_not_var_table.reserve(init_def_capacity);
        s_def_kind_table.reserve(init_def_capacity);
        s_def_index_table.reserve(init_def_capacity);
        
        // reserving against the worst-case: all constants or variables
        s_const_def_info_table.reserve(init_def_capacity);
        s_var_def_info_table.reserve(init_def_capacity);
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

    //
    // TODO: implement these functions
    //

    DefID define_const_exp(
        char const* mod_name,
        char const* def_name,
        NodeID node_id,
        bool is_global
    ) {
        return 0;
    }

}