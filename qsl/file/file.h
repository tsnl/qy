#pragma once

typedef void* File;

typedef int FileOpenFlag;
extern FileOpenFlag const FILE_OPEN_FLAG__BINARY;
extern FileOpenFlag const FILE_OPEN_FLAG__TEXT;
extern FileOpenFlag const FILE_OPEN_FLAG__CAN_READ;
extern FileOpenFlag const FILE_OPEN_FLAG__CAN_WRITE;

File file_open(void);
File file_close(void);
