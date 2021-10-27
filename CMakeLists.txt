cmake_minimum_required(VERSION 3.0.0)
project(Qy)

set(CMAKE_C_VERSION 11)
set(CMAKE_CXX_VERSION 20)

include_directories(
    src/
)

add_library(
    qcl
    src/qcl/ast.cc
    src/qcl/ast.hh
    src/qcl/feedback.cc
    src/qcl/feedback.hh
    src/qcl/intern.cc
    src/qcl/intern.hh
    src/qcl/lexer.cc
    src/qcl/lexer.hh
    src/qcl/parser.cc
    src/qcl/parser.hh
    src/qcl/reader.cc
    src/qcl/reader.hh
    src/qcl/typer.cc
    src/qcl/typer.hh
    src/qcl/types.cc
    src/qcl/types.hh
)
add_executable(
    qc3
    src/qc3/main.cc
)
target_link_libraries(
    qc3 PUBLIC qcl
)
