#include "print-v1.h"

#include <stdio.h>

void printLine(void) {
    printf("\n");
}
void printTab(void) {
    printf("\t");
}
void printInt(int v) {
    printf("%d", v);
}

struct File* fh1 = NULL;
struct File* fh2 = NULL;