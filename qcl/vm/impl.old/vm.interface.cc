#include "vm.interface.h"

#include <cstdlib>

#include "vm.impl.hh"

struct VM {
  public:
    qcl::VM_Impl impl;
  public:
    VM();
};

VM::VM()
:   impl{}
{}

VM* vm_create_wrapper();
void vm_destroy_wrapper(VM* vm);

VM* vm_create_wrapper() {
    return new VM();
}

void vm_destroy_wrapper(VM* vm) {
    delete vm;
}

VM* vm_create() {
    return vm_create_wrapper();
}
void vm_destroy(VM* vm) {
    vm_destroy_wrapper(vm);
}
