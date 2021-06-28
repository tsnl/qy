# distutils: language=c

from libc.string cimport memset
from libc.stdint cimport int8_t, int16_t, int32_t, int64_t, \
                         uint8_t, uint16_t, uint32_t, uint64_t


cdef union Register:
    int8_t i8
    int16_t i16
    int32_t i32
    int64_t i64

    uint8_t u8
    uint16_t u16
    uint32_t u32
    uint64_t u64

    float f16
    float f32
    double f64


# Each RegisterBlock is intended to fit in a 64-byte cache line.
cdef enum:
    REGISTERS_PER_BLOCK = 8
cdef struct RegisterBlock:
    Register data[REGISTERS_PER_BLOCK]


cdef:
    void register_clear(Register* rp)
    void register_block_clear(RegisterBlock* rbp)