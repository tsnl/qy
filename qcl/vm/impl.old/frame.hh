#pragma once

#include <map>

#include "int-str.hh"
#include "value.hh"

namespace qcl {

    class Frame;
    class OptBoundConstVal;

    class Frame {
      private:
        std::map<IntStr, OptBoundConstVal> m_context;
        Frame const* m_parent_frame;

      public:
        explicit Frame(Frame const* opt_parent_frame = nullptr)
        :   m_context{},
            m_parent_frame{opt_parent_frame}
        {};

      public:
        void define(IntStr name, OptBoundConstVal opt_val);
        OptBoundConstVal lookup(IntStr name) const;
        Frame* parent() const;
    };

    class OptBoundConstVal {
      private:
        Value m_value;
    };

}
