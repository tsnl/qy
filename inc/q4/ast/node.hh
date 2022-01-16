#pragma once

namespace q4 {
        
    class BaseNode;
    class BaseStmt;
    class BaseExp;

    using PNode = BaseNode*;
    using PStmt = BaseStmt*;
    using PExp = BaseExp*;

    class BaseNode {
      private:
        Span m_span;
      protected:
        BaseNode(Span span);
      public:
        BaseFileLoc* loc(Source* source) const { return source->alloc<FileSpanLoc>(source, m_span); }
    };
    class BaseStmt: public BaseNode {
      protected:
        BaseStmt(Span span);
    };
    class BaseExp: public BaseNode {
      protected:
        BaseExp(Span span);
    };

}