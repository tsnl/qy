# distutils: language=c++

from libc.stdint cimport uint32_t, uint64_t
from libcpp.vector cimport vector as vec

from .func cimport Func
from .frame cimport Frame


ctypedef vec[const Func*] FuncTableVec
ctypedef vec[Frame*] FrameStackVec

cdef:
    struct Interp:
        pass

    Interp* interp_create(uint64_t max_stack_offset)
    void interp_delete(Interp* interp)

    size_t interp_add_func(Interp* interp, const Func* func)

    uint64_t interp_alloca(Interp* interp, uint64_t alloc_size)

    uint64_t interp_get_stack_offset(Interp* interp)
    void interp_set_stack_offset(Interp* interp, uint64_t stack_offset)