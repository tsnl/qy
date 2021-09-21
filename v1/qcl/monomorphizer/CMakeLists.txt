cmake_minimum_required(VERSION 3.0)

project(CppMonomorphizerExt)

set(CMAKE_CXX_STANDARD 17)

include_directories(
    extension/
)
add_library(
    CppMonomorphizerExt STATIC

    extension/arg-list.cc
    extension/arg-list.hh
    extension/debug.hh
    extension/eval.cc
    extension/eval.hh
    extension/gdef.cc
    extension/gdef.hh
    extension/id-arg-list.hh
    extension/id-gdef.hh
    extension/id-intern.hh
    extension/id-mast.hh
    extension/id-modules.hh
    extension/id-mtype.hh
    extension/id-mval.hh
    extension/id-vcell.hh
    extension/intern.cc
    extension/intern.hh
    extension/mast.cc
    extension/mast.hh
    extension/modules.cc
    extension/modules.hh
    extension/mtype.cc
    extension/mtype.hh
    extension/mval.cc
    extension/mval.hh
    extension/panic.hh
    extension/printing.cc
    extension/printing.hh
    extension/shared-enums.cc
    extension/shared-enums.hh
    extension/stack.cc
    extension/stack.hh
    extension/sub.cc
    extension/sub.hh
    extension/vcell.cc
    extension/vcell.hh
)
