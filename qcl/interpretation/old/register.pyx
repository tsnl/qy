cdef:
    void register_clear(Register* rp):
        memset(rp, 0, sizeof(Register))

    void register_block_clear(RegisterBlock* rbp):
        memset(rbp, 0, sizeof(RegisterBlock))
