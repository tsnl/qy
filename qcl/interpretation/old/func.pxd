# distutils: language=c++

from libcpp.vector cimport vector as vec

from . cimport bb
from . cimport intstr


cdef:
    struct Func:
        vec[const bb.BasicBlock*] bb_vec
        int arg_type
        int ret_type
        intstr.IntStr name

    Func* func_create()
