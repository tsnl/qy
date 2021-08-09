# NOTE: we use CMake to build a static library that `setup.py` links against.

cmake_minimum_required(VERSION 3.0)

project(Extension)

set(CMAKE_CXX_STANDARD 17)

include_directories(
    extension/
)
add_library(
    ExtensionLib SHARED
    "extension/arg-list.cc"
    "extension/arg-list.hh"
    "extension/debug.hh"
    "extension/defs.cc"
    "extension/defs.hh"
    "extension/eval.cc"
    "extension/eval.hh"
    "extension/id-arg-list.hh"
    "extension/id-defs.hh"
    "extension/id-mast.hh"
    "extension/id-modules.hh"
    "extension/id-mtype.hh"
    "extension/id-mval.hh"
    "extension/mast.cc"
    "extension/mast.hh"
    "extension/modules.cc"
    "extension/modules.hh"
    "extension/mtype.cc"
    "extension/mtype.hh"
    "extension/mval.cc"
    "extension/mval.hh"
    "extension/panic.hh"
    "extension/shared-enums.hh"
    "extension/sub.cc"
    "extension/sub.hh"
)
