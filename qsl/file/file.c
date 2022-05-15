#include "files.h"

#include <stdio.h>

File open(void) {

}
File close(void) {

}

FileOpenFlag const FILE_OPEN__BINARY     = 0x1;
FileOpenFlag const FILE_OPEN__TEXT       = 0x2;
FileOpenFlag const FILE_OPEN__CAN_READ   = 0x4;
FileOpenFlag const FILE_OPEN__CAN_WRITE  = 0x8;

File THE_STDOUT = stdout;
File THE_STDERR = stderr;

File open(void) {

}
File close(void) {

}