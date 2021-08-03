#pragma once

#include <cstdint>

//
// Nodes are IDed by 64-bit handles
//

namespace monomorphizer {

    using NodeID = size_t;
    using ModID = NodeID;
    using ExpID = NodeID;
    using TypeSpecID = NodeID;
    using ElemID = NodeID;

    extern NodeID const NULL_NODE_ID;

}