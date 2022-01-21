cmake_minimum_required(VERSION 3.0.0)
project(q4 VERSION 0.0.0)

set(CMAKE_CXX_STANDARD 20)

set(ANTLR4_RUNTIME_SRC_DIR ${CMAKE_SOURCE_DIR}/dev/antlr4-cpp-runtime/source/runtime/src)
include_directories(
    ${ANTLR4_RUNTIME_SRC_DIR}
    ${ANTLR4_RUNTIME_SRC_DIR}/misc
    ${ANTLR4_RUNTIME_SRC_DIR}/atn
    ${ANTLR4_RUNTIME_SRC_DIR}/dfa
    ${ANTLR4_RUNTIME_SRC_DIR}/tree
    ${ANTLR4_RUNTIME_SRC_DIR}/support
    ${CMAKE_SOURCE_DIR}/gen/
    ${CMAKE_SOURCE_DIR}/inc/
)

set(Q4_PROJECT_VERSION CMAKE_PROJECT_VERSION)
set(Q4_CACHE_LINE_SIZE_IN_BYTES 64)
set(Q4_ENABLE_TRACES 1)
configure_file(
    ${CMAKE_SOURCE_DIR}/inc/q4/util/config.hh.in
    ${CMAKE_SOURCE_DIR}/inc/q4/util/config.hh
)

link_directories(${CMAKE_BINARY_DIR})
set(CMAKE_INSTALL_RPATH "$ORIGIN")
add_library(q4 SHARED IMPORTED src/q4/q4.cc)
add_library(q4_parser STATIC src/q4/parser/parser.cc gen/Q4SourceFileBaseVisitor.cpp gen/Q4SourceFileLexer.cpp gen/Q4SourceFileParser.cpp gen/Q4SourceFileVisitor.cpp)
add_library(q4_interp STATIC src/q4/interp/interp.cc src/q4/interp/scope.cc src/q4/interp/frame.cc)
add_library(q4_jit STATIC src/q4/jit/jit.cc)
add_library(q4_ast STATIC src/q4/ast/node.cc src/q4/ast/source.cc src/q4/ast/loc.cc)
add_library(q4_util STATIC src/q4/util/intern.cc)
target_link_libraries(q4_parser STATIC antlr4_static)
target_link_libraries(q4 INTERFACE q4_parser q4_jit q4_ast q4_util)

add_executable(q4c src/q4c/main.cc)
target_link_libraries(q4c INTERFACE q4)
