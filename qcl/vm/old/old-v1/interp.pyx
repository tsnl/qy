"""
Each `Interp` instance manages a pooled module containing function definitions of all discovered modules.
This pooling is achieved by treating the interpreter as a black-box, used to evaluate expressions.
- a new interpreter contains no code definitions
- functions can be loaded into a table, and can be accessed via a unique (incrementing int) ID
- we can load the AST into the interpreter in Python, run queries upon the interpreter to obtain key values,
  and even use reflection to obtain byte-code transcriptions for further emission.
"""

from qcl import excepts

from libc.stdlib cimport malloc, free
from .func cimport Func


cdef:
    struct Interp:
        FuncTableVec function_table
        FrameStackVec frame_stack
        uint64_t * stack_data
        uint64_t stack_offset
        uint64_t max_stack_offset


    Interp* interp_create(uint64_t max_stack_offset):
        block = <char*> malloc(
            sizeof(Interp) +    # interp block
            max_stack_offset    # stack block
        )
        interp = <Interp*> (block + 0)
        interp.function_table = FuncTableVec()
        interp.frame_stack = FrameStackVec()
        interp.stack_data = <uint64_t*> (block + sizeof(Interp))
        interp.stack_offset = 0
        interp.max_stack_offset = max_stack_offset
        return interp


    void interp_delete(Interp* interp):
        block = <char*> interp
        free(block)


    size_t interp_add_func(Interp* interp, const Func* func):
        func_ix = interp.function_table.size()
        interp.function_table.push_back(func)
        return func_ix

    uint64_t interp_alloca(Interp* interp, uint64_t alloc_size):
        returned_sp = interp.stack_offset
        interp.stack_offset += alloc_size
        if interp.stack_offset > interp.max_stack_offset:
            raise excepts.CheckerCompilationError("static-evaluation stack overflow")
        return returned_sp

    uint64_t interp_get_stack_offset(Interp* interp):
        return interp.stack_offset

    void interp_set_stack_offset(Interp* interp, uint64_t stack_offset):
        interp.stack_offset = stack_offset
