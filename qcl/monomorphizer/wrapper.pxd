from libc.stddef cimport size_t
from libc.stdint cimport *
from libcpp.string cimport string as cpp_string

#
#
# Externally linked types:
#
#

#
# Core:
#

cdef extern from "extension/shared-enums.hh" namespace "monomorphizer":
    ctypedef enum SES:
        SES_TOT = 0,
        SES_DV,
        SES_ST,
        SES_EXN,
        SES_ML

    ctypedef enum UnaryOp:
        UNARY_LOGICAL_NOT = 0,
        UNARY_DE_REF,
        UNARY_POS,
        UNARY_NEG

    ctypedef enum BinaryOp:
        BINARY_POW = 0,
        BINARY_MUL, BINARY_DIV, BINARY_REM,
        BINARY_ADD, BINARY_SUB,
        BINARY_LT, BINARY_LE, BINARY_GT, BINARY_GE,
        BINARY_EQ, BINARY_NE,
        BINARY_LOGICAL_AND,
        BINARY_LOGICAL_OR

    ctypedef enum AllocationTarget:
        ALLOCATION_TARGET_STACK = 0,
        ALLOCATION_TARGET_HEAP

    ctypedef enum IntegerSuffix:
        IS_U1 = 0,
        IS_U8,
        IS_U16,
        IS_U32,
        IS_U64,
        IS_S8,
        IS_S16,
        IS_S32,
        IS_S64

    ctypedef enum FloatSuffix:
        FS_F32 = 0,
        FS_F64


cdef extern from "extension/mast.hh" namespace "monomorphizer::mast":
    ctypedef enum NodeKind:
        # type-specifiers:
        TS_UNIT,
        TS_GID,
        TS_LID,
        TS_PTR,
        TS_ARRAY,
        TS_SLICE,
        TS_FUNC_SGN,
        TS_TUPLE,
        TS_GET_POLY_MODULE_FIELD,
        TS_GET_MONO_MODULE_FIELD,

        # expressions:
        EXP_UNIT,
        EXP_INT,
        EXP_FLOAT,
        EXP_STRING,
        EXP_LID,
        EXP_GID,
        EXP_TUPLE,
        EXP_FUNC_CALL,
        EXP_UNARY_OP,
        EXP_BINARY_OP,
        EXP_IF_THEN_ELSE,
        EXP_GET_TUPLE_FIELD,
        EXP_LAMBDA,
        EXP_ALLOCATE_ONE,
        EXP_ALLOCATE_MANY,
        EXP_CHAIN,
        EXP_GET_POLY_MODULE_FIELD,
        EXP_GET_MONO_MODULE_FIELD,
        EXP_CAST,

        # chain elements:
        ELEM_BIND1V,
        ELEM_BIND1T,
        ELEM_DO

#
# Arg Lists:
#

cdef extern from "extension/id-arg-list.hh" namespace "monomorphizer::arg_list":
    ctypedef size_t ArgListID

#
# Values:
#

cdef extern from "extension/mval.hh" namespace "monomorphizer::mval":
    ctypedef size_t VID

    void ensure_mval_init()

#
# Defs:
#

cdef extern from "extension/id-gdef.hh" namespace "monomorphizer":
    ctypedef size_t GDefID

cdef extern from "extension/gdef.hh" namespace "monomorphizer::gdef":
    ctypedef enum DefKind:
        BV_EXP,
        BV_TS,
        CONST_EXP,
        CONST_TS,
        CONST_TOT_VAL,
        CONST_TOT_TID


#
# Modules:
#

cdef extern from "extension/modules.hh" namespace "monomorphizer":
    ctypedef size_t MonoModID
    ctypedef size_t PolyModID


#
# Intern:
#

cdef extern from "extension/intern.hh" namespace "monomorphizer::intern":
    ctypedef size_t IntStr

#
# Mast:
#

cdef extern from "extension/id-mast.hh" namespace "monomorphizer::mast":
    ctypedef size_t NodeID
    ctypedef NodeID ExpID
    ctypedef NodeID TypeSpecID
    ctypedef NodeID ElemID

#
# MType/TID
#

cdef extern from "extension/id-mtype.hh" namespace "monomorphizer::mtype":
    ctypedef size_t TID

#
# mval:
#

cdef extern from "extension/mval.hh" namespace "monomorphizer::mval":
    enum ValueKind:
        VK_ERROR,
        VK_UNIT,
        VK_U1, VK_U8, VK_U16, VK_U32, VK_U64,
        VK_S8, VK_S16, VK_S32, VK_S64,
        VK_F32, VK_F64,
        VK_STRING,
        VK_TUPLE,
        VK_POINTER,
        VK_ARRAY,
        VK_SLICE,
        VK_FUNCTION
    
    struct CtxEnclosedId:
        IntStr name
        size_t target

    struct FuncInfo:
        uint32_t arg_name_count
        uint32_t ctx_enclosed_id_count
        IntStr* arg_name_array
        CtxEnclosedId* ctx_enclosed_id_array
        ExpID body_exp_id
        MonoModID mono_mod_id
    
    union ValueInfo:
        bint u1
        uint8_t u8
        uint16_t u16
        uint32_t u32
        uint64_t u64
        int8_t s8
        int16_t s16
        int32_t s32
        int64_t s64
        float f32
        double f64
        size_t string_info_index
        size_t sequence_info_index
        size_t func_info_index
        size_t ptr_info_index
        size_t slice_info_index
        size_t array_info_index


#
# V-Cell
#

cdef extern from "extension/vcell.hh" namespace "monomorphizer::vcell":
    ctypedef size_t VCellID


#
#
# Interface:
#
#

#
# Shared init:
#

cdef:
    void w_ensure_init();
    void w_drop();

#
# MAST: create expressions, type specs, and elems:
#

# expressions:
# - TODO: consider supporting local and global IDs separately
cdef:
    ExpID w_new_unit_exp(size_t source_index)
    ExpID w_new_int_exp(size_t mantissa, IntegerSuffix int_suffix, bint is_neg, size_t source_index)
    ExpID w_new_float_exp(double value, FloatSuffix float_suffix, size_t source_index)
    ExpID w_new_string_exp(size_t code_point_count, int* code_point_array, size_t source_index)
    ExpID w_new_lid_exp(IntStr int_str_id, size_t source_index)
    ExpID w_new_gid_exp(GDefID def_id, size_t source_index)
    ExpID w_new_func_call_exp(ExpID called_fn, ExpID arg_exp, bint call_is_non_tot, size_t source_index)
    ExpID w_new_tuple_exp(size_t item_count, ExpID* mv_item_array, size_t source_index)
    ExpID w_new_unary_op_exp(UnaryOp unary_op, ExpID arg_exp, size_t source_index)
    ExpID w_new_binary_op_exp(BinaryOp binary_op, ExpID lt_arg_exp, ExpID rt_arg_exp, size_t source_index)
    ExpID w_new_if_then_else_exp(ExpID cond_exp, ExpID then_exp, ExpID else_exp, size_t source_index)
    ExpID w_new_get_tuple_field_by_index_exp(ExpID tuple_exp_id, size_t index, size_t source_index)
    ExpID w_new_lambda_exp(
            uint32_t arg_name_count,
            IntStr* arg_name_array,
            uint32_t ctx_enclosed_name_count,
            IntStr* ctx_enclosed_name_array,
            ExpID body_exp,
            size_t source_index
    )
    ExpID w_new_allocate_one_exp(
        ExpID stored_val_exp_id, 
        AllocationTarget allocation_target, 
        bint allocation_is_mut,
        size_t source_index
    )
    ExpID w_new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bint allocation_is_mut,
        size_t source_index
    )
    ExpID w_new_chain_exp(
        size_t prefix_elem_id_count, 
        ElemID *mv_prefix_elem_id_array, 
        ExpID ret_exp_id,
        size_t source_index
    )
    ExpID w_new_get_mono_module_field_exp(
        MonoModID mono_mod_id, 
        size_t exp_field_ix,
        size_t source_index
    )
    ExpID w_new_get_poly_module_field_exp(
        PolyModID poly_mod_id, 
        size_t exp_field_ix,
        size_t arg_count, 
        NodeID* arg_array,
        size_t source_index
    )
    ExpID w_new_cast_exp(
        TypeSpecID ts_id, 
        ExpID exp_id, 
        size_t source_index
    )

# type-specs:
# - TODO: consider supporting local and global IDs separately
cdef:
    TypeSpecID w_new_unit_ts(size_t source_index)
    TypeSpecID w_new_gid_ts(GDefID def_id, size_t source_index)
    TypeSpecID w_new_lid_ts(IntStr int_str_id, size_t source_index)
    TypeSpecID w_new_ptr_ts(TypeSpecID ptd_ts, bint contents_is_mut, size_t source_index)
    TypeSpecID w_new_array_ts(TypeSpecID ptd_ts, ExpID count_exp, bint contents_is_mut, size_t source_index)
    TypeSpecID w_new_slice_ts(TypeSpecID ptd_ts, bint contents_is_mut, size_t source_index)
    TypeSpecID w_new_func_sgn_ts(TypeSpecID arg_ts, TypeSpecID ret_ts, SES ret_ses, size_t source_index)
    TypeSpecID w_new_tuple_ts(size_t elem_ts_count, TypeSpecID* mv_elem_ts_array, size_t source_index)
    TypeSpecID w_new_get_mono_module_field_ts(MonoModID mono_mod_id, size_t ts_field_ix, size_t source_index)
    TypeSpecID w_new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t ts_field_ix,
        size_t actual_arg_count,
        NodeID* actual_arg_array,
        size_t source_index
    )

# elements:
cdef:
    ElemID w_new_bind1v_elem(IntStr bound_def_id, ExpID init_exp_id, size_t source_index)
    ElemID w_new_bind1t_elem(IntStr bound_def_id, TypeSpecID init_ts_id, size_t source_index)
    ElemID w_new_do_elem(ExpID eval_exp_id, size_t source_index)

# get-info:

cdef extern from "extension/mast.hh" namespace "monomorphizer::mast":
    # Type-spec node infos:
    struct GlobalIdTypeSpecNodeInfo:
        GDefID def_id
    struct LocalIdTypeSpecNodeInfo:
        IntStr int_str_id
    struct PtrTypeSpecNodeInfo:
        TypeSpecID ptd_ts
        bint contents_is_mut
    struct ArrayTypeSpecNodeInfo:
        TypeSpecID ptd_ts
        ExpID count_exp
        bint contents_is_mut
    struct SliceTypeSpecNodeInfo:
        TypeSpecID ptd_ts
        bint contents_is_mut
    struct FuncSgnTypeSpecNodeInfo:
        TypeSpecID arg_ts
        TypeSpecID ret_ts
        SES ret_ses
    struct TupleTypeSpecNodeInfo:
        TypeSpecID* elem_ts_array
        size_t elem_ts_count
    struct GetPolyModuleFieldTypeSpecNodeInfo:
        size_t actual_arg_count
        NodeID* actual_arg_array
        PolyModID template_id
        size_t ts_field_index
    struct GetMonoModuleFieldTypeSpecNodeInfo:
        MonoModID template_id
        size_t ts_field_index
    
    # Expression node infos:
    struct IntExpNodeInfo:
        size_t mantissa
        IntegerSuffix suffix
        int is_neg
    struct FloatExpNodeInfo:
        double value
        FloatSuffix suffix
    struct StringExpNodeInfo:
        int* code_point_array
        size_t code_point_count
    struct GlobalIdExpNodeInfo:
        GDefID def_id
    struct LocalIdExpNodeInfo:
        IntStr int_str_id
    struct TupleExpNodeInfo:
        size_t item_count
        ExpID* item_array
    struct FuncCallExpNodeInfo:
        ExpID called_fn
        ExpID arg_exp_id
        int call_is_non_tot
    struct UnaryOpExpNodeInfo:
        ExpID arg_exp
        UnaryOp unary_op
    struct BinaryOpExpNodeInfo:
        ExpID lt_arg_exp
        ExpID rt_arg_exp
        BinaryOp binary_op
    struct IfThenElseExpNodeInfo:
        ExpID cond_exp
        ExpID then_exp
        ExpID else_exp
    struct GetTupleFieldExpNodeInfo:
        ExpID tuple_exp_id
        size_t index
    struct LambdaExpNodeInfo:
        uint32_t arg_name_count
        uint32_t ctx_enclosed_name_count
        IntStr* arg_name_array
        IntStr* ctx_enclosed_name_array
        ExpID body_exp
    struct AllocateOneExpNodeInfo:
        ExpID stored_val_exp_id
        AllocationTarget allocation_target
        bint allocation_is_mut
    struct AllocateManyExpNodeInfo:
        ExpID initializer_stored_val_exp_id
        ExpID alloc_count_exp
        AllocationTarget allocation_target
        bint allocation_is_mut
    struct ChainExpNodeInfo:
        ElemID* prefix_elem_array
        size_t prefix_elem_count
        ExpID ret_exp_id
    struct GetPolyModuleFieldExpNodeInfo:
        size_t arg_count
        NodeID* arg_array
        PolyModID template_id
        size_t field_index
    struct GetMonoModuleFieldExpNodeInfo:
        MonoModID template_id
        size_t field_index
    struct CastExpNodeInfo:
        TypeSpecID ts_id
        ExpID exp_id

    # element node infos:
    struct Bind1VElemNodeInfo:
        IntStr bound_id
        ExpID init_exp_id
    struct Bind1TElemNodeInfo: 
        IntStr bound_id
        TypeSpecID init_ts_id
    struct DoElemNodeInfo:
        ExpID eval_exp_id
    
    # putting it all together:
    union NodeInfo:
        # type-specs:
        GlobalIdTypeSpecNodeInfo ts_gid
        LocalIdTypeSpecNodeInfo ts_lid
        PtrTypeSpecNodeInfo ts_ptr
        ArrayTypeSpecNodeInfo ts_array
        SliceTypeSpecNodeInfo ts_slice
        FuncSgnTypeSpecNodeInfo ts_func_sgn
        TupleTypeSpecNodeInfo ts_tuple
        GetMonoModuleFieldTypeSpecNodeInfo ts_get_mono_module_field
        GetPolyModuleFieldTypeSpecNodeInfo ts_get_poly_module_field
        
        # expressions:
        IntExpNodeInfo exp_int
        FloatExpNodeInfo exp_float
        StringExpNodeInfo exp_str
        GlobalIdExpNodeInfo exp_gid
        LocalIdExpNodeInfo exp_lid
        TupleExpNodeInfo exp_tuple
        FuncCallExpNodeInfo exp_call
        UnaryOpExpNodeInfo exp_unary
        BinaryOpExpNodeInfo exp_binary
        IfThenElseExpNodeInfo exp_if_then_else
        GetTupleFieldExpNodeInfo exp_get_tuple_field
        LambdaExpNodeInfo exp_lambda
        AllocateOneExpNodeInfo exp_allocate_one
        AllocateManyExpNodeInfo exp_allocate_many
        ChainExpNodeInfo exp_chain
        GetMonoModuleFieldExpNodeInfo exp_get_mono_module_field
        GetPolyModuleFieldExpNodeInfo exp_get_poly_module_field
        CastExpNodeInfo exp_cast

        # elements:
        Bind1VElemNodeInfo elem_bind1v
        Bind1TElemNodeInfo elem_bind1t
        DoElemNodeInfo elem_do

cdef:
    NodeKind w_get_node_kind(NodeID node_id)
    NodeInfo* w_get_info_ptr(NodeID node_id)
    bint w_is_node_exp_not_ts(NodeID node_id)
    size_t w_get_source_node_index(NodeID node_id)

#
# Defs:
#

# constant definitions:
cdef:
    # declaring definitions for PolyModID fields:
    GDefID w_declare_global_def(DefKind kind, char* mv_def_name)

    # query definition info:
    bint w_get_def_is_bv(GDefID def_id)
    DefKind w_get_def_kind(GDefID def_id)
    const char* w_get_def_name(GDefID def_id)
    size_t w_get_def_target(GDefID def_id)
    void w_set_def_target(GDefID def_id, size_t target_id);


#
# Modules:
#

cdef:
    # Polymorphic template construction:
    # - add_field pushes a field and returns the field's unique index.
    PolyModID w_new_polymorphic_module(
        char* mv_template_name, 
        size_t bv_def_id_count, 
        GDefID* mv_bv_def_id_array,
        size_t source_node_index
    );
    size_t w_add_poly_module_field(PolyModID template_id, GDefID field_def_id);

    # Module fields are accessed by an index that is determined by the order
    # in which symbols are added.
    # By convention, this should be the order in which source nodes are written
    # in source code.
    size_t w_get_mono_mod_field_count(MonoModID mono_mod_id)
    GDefID w_get_mono_mod_field_at(MonoModID mono_mod_id, size_t field_index)
    PolyModID w_get_mono_mod_origin_poly_mod(MonoModID mono_mod_id)
    size_t w_get_mono_mod_source_node_index(MonoModID mono_mod_id)
    GDefID w_get_poly_mod_formal_arg_at(PolyModID poly_mod_id, size_t field_index)
    GDefID w_get_poly_mod_field_at(PolyModID poly_mod_id, size_t field_index)

    # instantiation:
    # turn a PolyModID into a MonoModID using some template arguments.
    MonoModID w_instantiate_poly_mod(PolyModID poly_mod_id, ArgListID arg_list_id);

    # reading back mono modules:
    size_t w_count_all_mono_modules()
    size_t w_count_registered_lambdas(MonoModID mono_mod_id)
    ExpID w_get_registered_lambda_at(MonoModID mono_mod_id, size_t index)

#
# Interning:
#

cdef:
    IntStr w_intern_string_1(cpp_string s, bint is_tid_not_vid)
    IntStr w_intern_string_2(const char* nt_bytes, bint is_tid_not_vid)
    cpp_string w_get_interned_string(IntStr int_str_id)
    bint w_is_interned_string_tid_not_vid(IntStr int_str_id)


#
# Printing:
#

cdef:
    void w_print_poly_mod(PolyModID poly_mod_id)
    void w_print_mono_mod(MonoModID mono_mod_id)


#
# ArgListID:
#

cdef:
    ArgListID w_empty_arg_list_id()


#
# MType:
#

cdef:
    TID w_get_unit_tid();
    TID w_get_u1_tid();
    TID w_get_u8_tid();
    TID w_get_u16_tid();
    TID w_get_u32_tid();
    TID w_get_u64_tid();
    TID w_get_s8_tid();
    TID w_get_s16_tid();
    TID w_get_s32_tid();
    TID w_get_s64_tid();
    TID w_get_f32_tid();
    TID w_get_f64_tid();
    TID w_get_string_tid();
    TID w_get_tuple_tid(ArgListID arg_list_id);
    TID w_get_ptr_tid(TID ptd_tid, bint contents_is_mut);
    TID w_get_array_tid(TID ptd_tid, VID count_val_id, bint contents_is_mut);
    TID w_get_slice_tid(TID ptd_tid, bint contents_is_mut);
    TID w_get_function_tid(TID arg_tid, TID ret_tid, SES ses);

#
# mval
#

cdef:
    ValueKind w_value_kind(VID value_id)
    ValueInfo w_value_info(VID value_id)
    size_t w_get_seq_count(VID value_id)
    bint w_get_seq_elem1(size_t seq_info_index, size_t index, VID* out_vid)
    bint w_get_seq_elem2(size_t tuple_val_id, size_t index, VID* out_vid)
    FuncInfo* w_get_func_info(size_t func_info_index)
    VCellID w_get_ptr_vcell(size_t ptr_info_index)
    size_t w_count_array_vcells(size_t array_info_index)
    size_t w_count_slice_vcells(size_t slice_info_index)
    VCellID w_get_array_vcell(size_t array_info_index, size_t index)
    VCellID w_get_slice_vcell(size_t slice_info_index, size_t index)
    bint w_equals(VID v1, VID v2)
    size_t w_count_str_code_points(size_t str_info_index);
    int w_get_str_code_point_at(size_t str_info_index, size_t code_point_index);

#
# vcell
#

cdef:
    VID w_get_vcell_val(VCellID vcell_id)