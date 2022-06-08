#include "file.h"

#include <stdio.h>
#include <string.h>

#define MAX_FILE_PATH_LENGTH 2048

///
// Implementation:
//

File help_open_file(char const* path_buf, int file_open_flags) {
    File file; {
        if (file_open_flags & (FILE_OPEN_FLAG__BINARY | FILE_OPEN_FLAG__CAN_READ)) {
            file = fopen(path_buf, "rb");
        } else if (file_open_flags & (FILE_OPEN_FLAG__BINARY | FILE_OPEN_FLAG__CAN_WRITE)) {
            file = fopen(path_buf, "wb");
        } else if (file_open_flags & (FILE_OPEN_FLAG__CAN_READ)) {
            file = fopen(path_buf, "r");
        } else if (file_open_flags & (FILE_OPEN_FLAG__CAN_WRITE)) {
            file = fopen(path_buf, "w");
        }
    }
    return file;
}

///
// Interface:
//

FileOpenFlag const FILE_OPEN_FLAG__BINARY     = 0x1;
FileOpenFlag const FILE_OPEN_FLAG__CAN_READ   = 0x2;
FileOpenFlag const FILE_OPEN_FLAG__CAN_WRITE  = 0x4;

File file_stdout = NULL;
File file_stderr = NULL;
__attribute__((constructor))
static void __file_init() {
    file_stdout = stdout;
    file_stderr = stderr;
}

File file_open1(String file_path, int file_open_flags) {
    return help_open_file(file_path.nt_data, file_open_flags);
}
File file_open2(StringView file_path, int file_open_flags) {
    char path_buf[MAX_FILE_PATH_LENGTH];
    strncpy(path_buf, file_path.src->nt_data + file_path.span.beg, string_view_length(&file_path));
    return help_open_file(path_buf, file_open_flags);
}
void file_print(File file, String print) {
    fprintf(file, "%s", print.nt_data);
}
void file_close(File file) {
    fclose(file);
}