// Symbols imported from C source code is automatically prefixed by `cx_` or `Cx_`

#pragma once

#include <stdint.h>

// FIXME: move this to 'qyl' library
// #define QY_FUNC __declspec(dllexport)

struct File;

enum FileAccess {
    FILE_ACCESS__READ,
    FILE_ACCESS__WRITE
};
enum FileType {
    FILE_TYPE__TEXT,
    FILE_TYPE__BINARY
};

extern struct File* fh1;
extern struct File* fh2;

void printLine(void);
void printTab(void);
void printInt(int v);
// struct File* openFile(char const* path, enum FileAccess access, enum FileType file_type);
// () closeFile(struct File* handle);
// int readCharFromFile(struct File* f);