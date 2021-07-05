# distutils: language=c++

from libc.stdint cimport uint8_t, uint16_t, uint32_t, uint64_t, int8_t, int16_t, int32_t, int64_t

from .interp cimport Interp
from .register cimport Register


cdef:
    struct Frame:
        pass

    Frame* frame_create(Interp* interp)
    void frame_delete(Frame* frame)

    uint32_t frame_push_reg(Frame* frame);
    Register frame_get_reg(Frame* frame, uint32_t index)
    void frame_set_reg(Frame* frame, uint32_t index, Register reg)

    uint32_t frame_set_reg_i8(Frame* frame, uint32_t rix, int8_t v)
    uint32_t frame_set_reg_i16(Frame* frame, uint32_t rix, int16_t v)
    uint32_t frame_set_reg_i32(Frame* frame, uint32_t rix, int32_t v)
    uint32_t frame_set_reg_i64(Frame* frame, uint32_t rix, int64_t v)

    uint32_t frame_set_reg_u8(Frame * frame, uint32_t rix, uint8_t v)
    uint32_t frame_set_reg_u16(Frame * frame, uint32_t rix, uint16_t v)
    uint32_t frame_set_reg_u32(Frame* frame, uint32_t rix, uint32_t v)
    uint32_t frame_set_reg_u64(Frame* frame, uint32_t rix, uint64_t v)

    uint32_t frame_set_reg_f32(Frame* frame, uint32_t rix, float v)
    uint32_t frame_set_reg_f64(Frame* frame, uint32_t rix, double v)
