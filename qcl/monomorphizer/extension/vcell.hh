#pragma once

#include "id-vcell.hh"
#include "id-mval.hh"

namespace monomorphizer::vcell {

    extern VCellID const NULL_VCELL_ID;

    void ensure_init();
    
    VCellID push_vcell(mval::VID init_vid);
    void set_vcell_val(VCellID vcell_id, mval::VID new_vid);
    mval::VID get_vcell_val(VCellID vcell_id);

}