cdef:
    BasicBlock* create(Interp* interp):
        pass

    void destroy(BasicBlock* bb):
        pass

    uint32_t build_imul(BasicBlock* bb, uint32_t lhs_rix, uint32_t rhs_rix):
        pass

    uint32_t build_idiv(BasicBlock* bb, uint32_t lhs_rix, uint32_t rhs_rix):
        pass

    uint32_t build_irem(BasicBlock* bb, uint32_t lhs_rix, uint32_t rhs_rix):
        pass

    uint32_t build_iadd(BasicBlock * bb, uint32_t lhs_rix, uint32_t rhs_rix):
        pass
