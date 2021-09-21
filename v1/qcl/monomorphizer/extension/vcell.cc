#include "vcell.hh"

#include <vector>
#include <limits>
#include <cassert>

namespace monomorphizer::vcell {

    VCellID const NULL_VCELL_ID = std::numeric_limits<VCellID>::max();

    static std::vector<mval::VID> s_cell_vid_table;
    static size_t const s_default_cell_vid_table_capacity = 64 * 1024;

    void ensure_init() {
        s_cell_vid_table.reserve(s_default_cell_vid_table_capacity);
    }

    VCellID push_vcell(mval::VID init_vid) {
        VCellID cell_id = s_cell_vid_table.size();
        s_cell_vid_table.push_back(init_vid);
        return cell_id;
    }
    void set_vcell_val(VCellID vcell_id, mval::VID new_vid) {
        assert(vcell_id != NULL_VCELL_ID);
        s_cell_vid_table[vcell_id] = new_vid;
    }
    mval::VID get_vcell_val(VCellID vcell_id) {
        return s_cell_vid_table[vcell_id];
    }

 }