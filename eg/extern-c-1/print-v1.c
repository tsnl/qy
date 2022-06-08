#include "print-v1.h"

#include <stdio.h>

void pv1_printLine(void) {
    printf("\n");
}
void pv1_printTab(void) {
    printf("\t");
}
void pv1_printInt(int v) {
    printf("%d", v);
}
void pv1_printLong(long long v) {
    printf("%llu", v);
}

struct PV1_File* fh1 = NULL;
struct PV1_File* fh2 = NULL;