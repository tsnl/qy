#pragma once

#include "loc.hh"
#include "source.hh"

namespace q4 {

class BaseNode {
  private:
    Span m_span;
  public:
    BaseNode(Span span);
  public:
    BaseFileLoc* loc(Source* source) const { return source->alloc<FileSpanLoc>(source, m_span); }
};

}