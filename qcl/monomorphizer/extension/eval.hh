// `eval` generates tree-shaked template instantiations by way of evaluating
// constants.
// The idea is: we evaluate each global constant bound in modules totally ahead 
// of time.
// This total evaluation uses monomorphization: all used template submodules are 
// instantiated as monomorphic submodules before 'evaluation'.
// This total evaluation verifies initialization order.
//  - if we are unable to eagerly compute a definition's value, we must report
//    an error.
//  - thus, BEWARE OF CYCLES
//  - NOTE: two kinds of dependencies: delayed and immediate:
//      - delayed dependency: ID referenced in a function's body
//          - e.g. `x` in `bound := () -> {x}`
//      - immediate dependency: ID value must be known to compute another val
//          - e.g. `x` in `bound := 2*x`
//      - only immediate dependencies should generate errors, but we should 
//        still monomorphize delayed dependencies
//      - HENCE: 
//
//
//      TODO: write 2 (families of) functions: 
//          (1) monomorphize_it: returns monomorphic version of TS/Exp
//          (2) evaluate_it: 
//                  - returns mval::ValueID or mtype::MTypeID
//                  - only accepts monomorphic input
//      Invoke 'monomorphize' for delayed deps (i.e. any lambda body)
//      Invoke 'monomorphize', then 'evaluate' for immediate deps.
//
//

#pragma once

#include "id-mast.hh"
#include "id-mtype.hh"
#include "id-mval.hh"

namespace monomorphizer::eval {

    // NOTE: these functions could throw errors 
    mtype::MTypeID eval_type(mast::TypeSpecID ts_id);
    mval::ValueID eval_exp(mast::ExpID exp_id);

}
