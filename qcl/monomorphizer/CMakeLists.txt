# NOTE: we use CMake to build a static library that `setup.py` links against.

cmake_minimum_required(VERSION 3.0)

project(Extension)

set(CMAKE_CXX_STANDARD 17)

include_directories(
    extension/
)
add_library(
    ExtensionLib SHARED
    "extension/copier.cc"
    "extension/mast.cc"
    "extension/defs.cc"
    "extension/eval.cc"
)
