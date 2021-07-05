#include "vm.hh"

#include <cstdlib>
#include <vector>

#include "alloc.hh"

//
// Function & Basic Block implementations
//

enum OpCode {
    //
    // tier 1: simple instructions
    //

    // bao: binary arithmetic operators
    OP_IMUL, OP_IADD, OP_ISUB,
    OP_FMUL, OP_FADD, OP_FSUB,
    OP_SDIV, OP_UDIV, OP_FDIV,
    OP_SREM, OP_UREM, OP_FREM,

    // cmp: binary comparison operators
    OP_IEQ, OP_INE,
    OP_FEQ, OP_FNE,
    OP_ULE, OP_UGE, OP_ULT, OP_UGT,
    OP_SLE, OP_SGE, OP_SLT, OP_SGT,
    OP_FLE, OP_FGE, OP_FLT, OP_FGT,

    // load/store:
    OP_LOAD_U, OP_LOAD_S, OP_LOAD_F,
    OP_STORE_U, OP_STORE_S, OP_STORE_F,

    // function call:
    OP_CALL,

    // allocation:
    OP_ALLOCATE,

    // setting constants in registers:
    OP_SET_REG_U, OP_SET_REG_S, OP_SET_REG_F,

    // control-flow:
    OP_BR, OP_PHI, OP_RET,

    //
    // tier 2: complex instructions: can be rewritten using tier 1
    //

    OP_MEMCPY,
    OP_PUSH,
    OP_POP,
};

union OpArgs {
    struct {
        RegisterID lhs_reg_id;
        RegisterID rhs_reg_id;
        RegisterID dst_reg_id;
    } bao;

    struct {
        RegisterID lhs_reg_id;
        RegisterID rhs_reg_id;
        RegisterID dst_reg_id;
    } cmp;

    struct {
        RegisterID ptr_reg_id;
        RegisterID dst_reg_id;
    } load;

    struct {
        RegisterID ptr_reg_id;
        RegisterID src_reg_id;
    } store;

    struct {
        RegisterID func_reg_id;
    } call;

    struct {
        RegisterID size_reg_id;
        RegisterID dst_reg_id;
    } allocate;

    struct {
        RegisterID reg_id;
        Register value;
    } set_reg;

    struct {
        RegisterID condition_reg_id;
        BasicBlockID bb_if_true;
        BasicBlockID bb_if_false;
    } br;

    struct {
        RegisterID dst_reg_id;
        Register incoming_edge_count;
        BasicBlockID* incoming_edges;
    } phi;
};

struct Instr {
    OpCode op_code;
    OpArgs op_args;
};

struct BasicBlock {
    std::vector<Instr> instr_list;
};

struct Function {
    // todo: implement me
};

//
// Frame implementations
//

struct Frame {
    // todo: implement me
};

//
// VM implementation
//

struct VM {
    Register registers[VM_REGISTER_COUNT];
    std::vector<Function> functions;
    std::vector<Frame> frame_stack;
    LinearAllocator stack;
    LinearAllocator heap;
};

