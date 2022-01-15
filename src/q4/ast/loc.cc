#include "q4/ast/loc.hh"

#include <sstream>
#include "q4/ast/source.hh"

namespace q4 {
    std::ostream& FileSpanLoc::operator<< (std::ostream& out) const {
        out << source()->path()
            << ":" << 1+m_span.first.lineIx << ":" << 1+m_span.first.colIx 
            << " - " << 1+m_span.last.lineIx << ":" << 1+m_span.last.colIx;
        return out;
    }
    std::ostream& FilePosLoc::operator<< (std::ostream& out) const {
        out << source()->path()
            << ":" << 1+m_pos.lineIx << ":" << 1+m_pos.colIx;
        return out;
    }
}
