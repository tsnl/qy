// Symbols imported from C source code is automatically prefixed by `cx_` or `Cx_`

#pragma once

#include <stdint.h>

// #define QY_PRINT_V1_MAX_OPEN_FILE_COUNT (42)

// int x;

// struct File;

// enum FileAccess {
//     FILE_ACCESS__READ,
//     FILE_ACCESS__WRITE
// };
// enum FileType {
//     FILE_TYPE__TEXT,
//     FILE_TYPE__BINARY
// };

// void printUtf8Char(char c);
// File* openFile(char const* path, FileAccess access, FileType file_type);
// void closeFile(File* handle);
// int readCharFromFile(File* f);

// #define RETURN_PREFIX inline static int 

// RETURN_PREFIX round_shr(size_t x, size_t s) { return (s == 0 ? x : ((x + (1 << (s-1))) >> s)); }

#define ROUND_SHR(X, S) (round_shr((X), (S)))

// would be automatically exposed in Qy as...
// CX_File
// cx_printUtf8Char
// cx_openFile
// cx_closeFile
