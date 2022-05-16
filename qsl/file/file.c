#include "file.h"

#include <stdio.h>

FileOpenFlag const FILE_OPEN__BINARY     = 0x1;
FileOpenFlag const FILE_OPEN__TEXT       = 0x2;
FileOpenFlag const FILE_OPEN__CAN_READ   = 0x4;
FileOpenFlag const FILE_OPEN__CAN_WRITE  = 0x8;

File file_open1(StringView file_path, int file_open_flags) {
    
}
File file_open2(String* file_path_ref, int file_open_flags) {

}
File file_close(File file) {

}