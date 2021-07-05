from libc.stdlib cimport malloc, free
from libc.string cimport memset

from libcpp.vector cimport vector as vec

from .register cimport Register, RegisterBlock, REGISTERS_PER_BLOCK, register_clear, register_block_clear
from .interp cimport interp_get_stack_offset


cdef:
    struct Frame:
        vec[RegisterBlock] register_blocks
        uint64_t beg_stack_offset
        Interp * interp
        uint32_t register_count

    Frame* frame_create(Interp* interp):
        fp = <Frame*> malloc(sizeof(Frame))
        fp.register_blocks.reserve(1)
        fp.beg_stack_offset = interp_get_stack_offset(interp)
        fp.interp = interp
        fp.register_count = 0
        return fp

    void frame_delete(Frame* frame):
        free(frame)

    uint32_t frame_push_reg(Frame* frame):
        rix = frame.register_count

        # the register count increments by 1 each time.

        # if the current register count is a multiple of the number of registers per register-block,
        # then we must push a new register block which is guaranteed to have enough space for the new
        # register (since each RegisterBlock has more than 1 element)

        if frame.register_count % REGISTERS_PER_BLOCK == 0:
            fresh_rb: RegisterBlock
            register_block_clear(&fresh_rb)
            frame.register_blocks.push_back(fresh_rb)

        frame.register_count = 1 + frame.register_count

    Register frame_get_reg(Frame* frame, uint32_t index):
        block_index = index / REGISTERS_PER_BLOCK
        block_offset = index % REGISTERS_PER_BLOCK
        reg = <Register> frame.register_blocks[block_index].data[block_offset]
        return reg

    void frame_set_reg(Frame* frame, uint32_t index, Register reg):
        block_index = index / REGISTERS_PER_BLOCK
        block_offset = index % REGISTERS_PER_BLOCK
        frame.register_blocks[block_index].data[block_offset] = reg

    uint32_t frame_set_reg_i8(Frame* frame, uint32_t rix, int8_t v):
        reg: Register
        register_clear(&reg)
        reg.i8 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_i16(Frame* frame, uint32_t rix, int16_t v):
        reg: Register
        register_clear(&reg)
        reg.i16 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_i32(Frame* frame, uint32_t rix, int32_t v):
        reg: Register
        register_clear(&reg)
        reg.i32 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_i64(Frame* frame, uint32_t rix, int64_t v):
        reg: Register
        register_clear(&reg)
        reg.i64 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_u8(Frame* frame, uint32_t rix, uint8_t v):
        reg: Register
        register_clear(&reg)
        reg.u8 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_u16(Frame* frame, uint32_t rix, uint16_t v):
        reg: Register
        register_clear(&reg)
        reg.u16 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_u32(Frame* frame, uint32_t rix, uint32_t v):
        reg: Register
        register_clear(&reg)
        reg.u32 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_u64(Frame* frame, uint32_t rix, uint64_t v):
        reg: Register
        register_clear(&reg)
        reg.u64 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_f32(Frame* frame, uint32_t rix, float v):
        reg: Register
        register_clear(&reg)
        reg.f32 = v
        frame_set_reg(frame, rix, reg)
        return rix

    uint32_t frame_set_reg_f64(Frame* frame, uint32_t rix, double v):
        reg: Register
        register_clear(&reg)
        reg.f64 = v
        frame_set_reg(frame, rix, reg)
        return rix
