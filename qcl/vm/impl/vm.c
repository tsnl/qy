#include "vm.h"

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

#include "table.h"
#include "expr.h"

//
//
// Internal forward declarations:
//
//

//
// Type declarations
//

//
// Function declarations:
//

// vm:
VM* vm_create_impl();
void vm_destroy_impl(VM* vm);

//
//
// Type definitions:
//
//

//
// Expressions:
//

//
// VM:
//

struct VM {
    Table* expr_tab;
};

//
//
// Implementation:
//
//

VM* vm_create_impl() {
    VM* vm = malloc(sizeof(VM));
    vm->expr_tab = expr_tab_init();
    return vm;
}

void vm_destroy_impl(VM* vm) {
    expr_tab_destroy(vm->expr_tab);
    free(vm);
}

//
// Expr Tables:
//

//
//
// Interface:
//
//

//
// VM management:
//

VM* vm_create() {
    return vm_create_impl();
}

void vm_destroy(VM* vm) {
    free(vm);
}

// todo: hook into `expr` to implement 'expr' builders