#include "q4/ast/node.hh"

// expressions:
namespace q4 {
    bool BaseLiteralBoolExp::is_t() const { return !!dynamic_cast<TLiteralBoolExp const*>(this); }
    bool BaseLiteralBoolExp::is_f() const { return !!dynamic_cast<FLiteralBoolExp const*>(this); }
}
