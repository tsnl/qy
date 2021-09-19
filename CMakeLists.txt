cmake_minimum_required(VERSION 3.0.0)
project(QyBuild)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fconstexpr-depth=1000000 -fconstexpr-steps=100000000")

add_executable(
    output-1
    qy-build/output-1.cpp
)

