#pragma once

#include "loc.hh"
#include "source.hh"
#include "node.hh"
#include "exp.hh"
#include "stmt.hh"

namespace q4 {
    template <typename T, typename... TArgs> T* newAstNode(Source* source, TArgs... args);
}

// Inline implementation:
namespace q4 {
    template <typename T, typename... TArgs>
    T* newAstNode(Source* source, Span span, TArgs... args) {
        return source->alloc<T>(span, args...);
    }
}