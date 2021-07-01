# distutils: language = c++

from libc.stdlib cimport malloc, free
from libc.stdint cimport uint64_t
from libcpp.deque cimport deque
from libcpp.map cimport map


ctypedef uint64_t IntStr

cdef extern from "vm-impl/vm.interface.h":
    struct VM

    VM* vm_new()
    void vm_del(VM* vm)
