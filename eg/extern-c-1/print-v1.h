// Symbols imported from C source code is automatically prefixed by `cx_` or `Cx_`

#pragma once

#include <stdint.h>

// FIXME: move this to 'qyl' library
// #define QY_FUNC __declspec(dllexport)

struct PV1_File;

enum PV1_FileAccess {
    FILE_ACCESS__READ,
    FILE_ACCESS__WRITE
};
enum PV1_FileType {
    FILE_TYPE__TEXT,
    FILE_TYPE__BINARY
};

extern struct PV1_File* fh1;
extern struct PV1_File* fh2;

void pv1_printLine(void);
void pv1_printTab(void);
void pv1_printInt(int v);
void pv1_printLong(long long v);
// struct File* openFile(char const* path, enum FileAccess access, enum FileType file_type);
// () closeFile(struct File* handle);
// int readCharFromFile(struct File* f);