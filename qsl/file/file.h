#pragma once

#include "../string/string.h"
#include "../string/string-view.h"

typedef void* File;

typedef int FileOpenFlag;
extern FileOpenFlag const FILE_OPEN_FLAG__BINARY;
extern FileOpenFlag const FILE_OPEN_FLAG__CAN_READ;
extern FileOpenFlag const FILE_OPEN_FLAG__CAN_WRITE;

File file_open1(String file_path, int file_open_flags);
File file_open2(StringView file_path, int file_open_flags);

void file_print(File file, String print);

void file_close(File file);
