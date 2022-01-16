#!/usr/bin/env bash

NAMESPACE=q4
GRAMMAR_PATH=grammars/Q4SourceFile.g4
CORRECT_CWD_TOKEN=correct-cwd-token-48018.txt
ANTLR_SOURCE_TEST_FILE_PATH=dev/antlr4-cpp-runtime/source/CMakeLists.txt
ANTLR_BUILD_TEST_FILE_PATH=dev/antlr4-cpp-runtime/build/CMakeCache.txt

if [ ! -f ${CORRECT_CWD_TOKEN} ]; then
    echo "ERROR:  Could not locate correct current-working-directory token named '${CORRECT_CWD_TOKEN}'."
    echo "        Please run this script from that directory instead."
    exit 1
fi

if [[ "$1" == "clean" ]]; then
    echo "INFO:   Cleaning..."
    rm -rf dev/antlr4-cpp-runtime
fi 

if [ ! -f ${ANTLR_SOURCE_TEST_FILE_PATH} ]; then
    mkdir -p dev/antlr4-cpp-runtime/build dev/antlr4-cpp-runtime/source
    unzip dev/antlr4-cpp-runtime-4.9.3-source.zip -d dev/antlr4-cpp-runtime/source/
fi

if [ ! -f ${ANTLR_BUILD_TEST_FILE_PATH} ]; then
    mkdir -p dev/antlr4-cpp-runtime/build
    mkdir -p dev/antlr4-cpp-runtime/install
    pushd dev/antlr4-cpp-runtime/build
        cmake ../source -DCMAKE_BUILD_TYPE=RelWithDebInfo
        cmake --build . --parallel $(nproc)
        cmake --build .     # in case of clock skew
    popd
fi

java -jar dev/antlr-4.9.3-complete.jar $(realpath $GRAMMAR_PATH) -no-listener -visitor -o gen/ -package ${NAMESPACE}

exit 0
