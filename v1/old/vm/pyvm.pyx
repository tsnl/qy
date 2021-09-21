# distutils: language = c

from libc.stdlib cimport malloc, free
from libc.stdint cimport uint64_t


ctypedef uint64_t IntStr

cdef extern from "impl/vm.h":
    struct VM

    VM* vm_create()
    void vm_destroy(VM* vm)

0