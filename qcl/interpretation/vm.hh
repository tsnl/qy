#pragma once

#include <cstdint>

#include <vector>

#define VM_REGISTER_COUNT (16)

typedef struct VM VM;
typedef uint64_t FunctionID;
typedef uint64_t BasicBlockID;
typedef uint64_t BasicBlockInstrID;
typedef union Register Register;
typedef struct PHIIncomingEdge PHIIncomingEdge;

//
//
// Enum Definitions:
//
//

enum RegisterID {
    R0 = 0,
    R1 = 1,
    R2 = 2,
    R3 = 3,
    R4 = 4,
    R5 = 5,
    R6 = 6,
    R7 = 7,
    R8 = 8,
    R9 = 9,
    R10 = 10,
    R11 = 11,
    R12 = 12,
    R13 = 13,
    R14 = 14,
    R15 = 15,
    RBP,
    RSP,
    RAX,
    META_REGISTER_COUNT
};
enum BinArithOp {
    BAO_POW,
    BAO_MUL, BAO_DIV, BAO_REM,
    BAO_ADD, BAO_SUB
};
enum CmpOp {
    BAO_LT, BAO_GT, BAO_LE, BAO_GE,
    BAO_EQ, BAO_NE
};
enum RegType {
    RT_I8, RT_I16, RT_I32, RT_I64,
    RT_U8, RT_U16, RT_U32, RT_U64,
    RT_F32, RT_F64
};
enum Allocator {
    ALLOCATOR_STACK,
    ALLOCATOR_HEAP
};

//
//
// Interface:
//
//

// creation/destruction:
VM* vm_create();
void vm_destroy(VM* vm);

// function management:
FunctionID vm_append_new_func(VM* vm, char const* name);
BasicBlockID vm_append_new_bb(VM* vm, FunctionID func_id);
void vm_set_func_entry_point_bb(VM* vm, FunctionID func_id, BasicBlockID bb);

//
// BB builder functions:
// append instructions to a basic block
//

//
// type 1: basic instructions
//

BasicBlockInstrID vm_build_bao(
    VM* vm, BasicBlockID bb_id,
    BinArithOp bin_arith_op, RegType reg_type,
    RegisterID lhs_reg_id, RegisterID rhs_reg_id,
    RegisterID dst_reg_id
);
BasicBlockInstrID vm_build_cmp(
    VM* vm, BasicBlockID bb_id,
    CmpOp cmp_op, RegType reg_type,
    RegisterID lhs_reg_id, RegisterID rhs_reg_id,
    RegisterID dst_reg_id
);
BasicBlockInstrID vm_build_load(
    VM* vm, BasicBlockID bb_id,
    RegType reg_type,
    RegisterID ptr_reg_id, RegisterID dst_reg_id
);
BasicBlockInstrID vm_store(
    VM* vm, BasicBlockID bb_id,
    RegType reg_type,
    RegisterID ptr_reg_id, RegisterID src_reg_id
);
BasicBlockInstrID vm_build_call(
    VM* vm, BasicBlockID bb_id,
    RegisterID func_reg_id
);
BasicBlockInstrID vm_build_allocate(
    VM* vm, BasicBlockID bb_id,
    Allocator allocator,
    RegisterID size_reg_id,
    RegisterID dst_reg_id
);
BasicBlockInstrID vm_build_set_reg(
    VM* vm, BasicBlockID bb_id,
    RegisterID reg_id,
    Register value
);
BasicBlockInstrID vm_build_br(
    VM* vm, BasicBlockID bb_id,
    RegisterID condition_reg_id,
    BasicBlockID bb_if_true,
    BasicBlockID bb_if_false
);
BasicBlockInstrID vm_build_phi(
    VM* vm, BasicBlockID bb_id,
    RegisterID dst_reg_id,
    std::vector<PHIIncomingEdge> branches
);
BasicBlockInstrID vm_build_memcpy(
    VM* vm, BasicBlockID bb_id,
    RegisterID dst_ptr_reg_id, RegisterID src_ptr_reg_id,
    RegisterID size_in_bytes_reg_id
);
BasicBlockInstrID vm_build_ret(
    VM* vm, BasicBlockID bb_id,
    RegisterID copy_to_rax_reg_id
);

//
// type 2: complex instructions: can be implemented in terms of basic instructions if desired
//

// lea = load effective address
// equivalent to `load` from {ptr = base + slope * ordinate}
BasicBlockInstrID vm_build_lea(
    VM* vm, BasicBlockID bb_id,
    RegType reg_type,
    RegisterID base_address_reg_id,
    RegisterID slope_reg_id,
    RegisterID ordinate_reg_id,
    RegisterID dst_reg_id
);

// push/pop: used to manipulate contents of the stack using registers
// - a proxy for 'alloca', then 'load'/'store'
// - unlike real machines, 'push' increments the stack pointer rather than decrement it
// - mutates the `stack-pointer` register
BasicBlockInstrID vm_build_push(
    VM* vm, BasicBlockID bb_id,
    RegType reg_type,
    RegisterID src_reg_id
);
BasicBlockInstrID vm_build_pop(
    VM* vm, BasicBlockID bb_id,
    RegType reg_type,
    RegisterID dst_reg_id
);

//
// poke: interpreter manipulation to configure stuff:
// named 'poke' because it involves manipulating the VM state without code, by 'poking' at it from outside rather than
// from within.
//

void vm_poke_set_reg(VM* vm, RegisterID reg_id, Register value);
Register vm_poke_get_reg(VM* vm, RegisterID reg_id);
Register vm_poke_load(
    VM* vm,
    RegType reg_type,
    RegisterID ptr_reg_id, RegisterID dst_reg_id
);
Register vm_poke_lea(
    VM* vm,
    RegType reg_type,
    RegisterID base_address_reg_id, RegisterID slope_reg_id, RegisterID ordinate_reg_id,
    RegisterID dst_reg_id
);
void vm_poke_store(VM* vm, RegType reg_type, RegisterID ptr_reg_id, RegisterID src_reg_id);
void vm_poke_push(VM* vm, RegType reg_type, RegisterID src_reg_id);
Register vm_poke_pop(VM* vm, RegType reg_type);
void vm_poke_call(VM* vm, RegisterID func_reg_id);


//
//
//
// Inline type definitions:
//
//
//

union Register {
    int8_t i8;
    int16_t i16;
    int32_t i32;
    int64_t i64;

    uint8_t u8;
    uint16_t u16;
    uint32_t u32;
    uint64_t u64;

    float f32;
    double f64;

    uint8_t* ptr;
    FunctionID func_id;
    BasicBlockID bb_id;
};
struct PHIIncomingEdge {
    BasicBlockID src_bb_id;
    RegisterID src_reg_id;
};