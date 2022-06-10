#pragma once

#include "../string/string.h"
#include "../string/string-view.h"
#include "../prim/integer.h"

typedef void* File;

extern File file_stdout;
extern File file_stderr;

typedef int FileOpenFlag;
extern FileOpenFlag const FILE_OPEN_FLAG__BINARY;
extern FileOpenFlag const FILE_OPEN_FLAG__CAN_READ;
extern FileOpenFlag const FILE_OPEN_FLAG__CAN_WRITE;

File file_open1(String file_path, int file_open_flags);
File file_open2(StringView file_path, int file_open_flags);

i32 file_read_bytes(File file, i32 data_capacity, u8* data);
void file_print(File file, String print);

void file_close(File file);
