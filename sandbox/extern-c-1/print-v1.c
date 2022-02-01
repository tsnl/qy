#include "print-v1.h"

#include <stdio.h>

void printInt(int v) {
    printf("%d\n", v);
}

struct File* fh1 = NULL;
struct File* fh2 = NULL;