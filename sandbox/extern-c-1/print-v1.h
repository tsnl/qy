// Symbols imported from C source code is automatically prefixed by `cx_` or `Cx_`

#pragma once

#include <stdint.h>

// #define QY_PRINT_V1_MAX_OPEN_FILE_COUNT (42)

// int x;

struct File;

enum FileAccess {
    FILE_ACCESS__READ,
    FILE_ACCESS__WRITE
};
enum FileType {
    FILE_TYPE__TEXT,
    FILE_TYPE__BINARY
};

File* stdout;
File* stderr;

void printUtf8Char(char c);
File* openFile(char const* path, FileAccess access, FileType file_type);
void closeFile(File* handle);
int readCharFromFile(File* f);
