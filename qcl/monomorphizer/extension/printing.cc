#include "printing.hh"

#include <iostream>
#include <iomanip>

#include "modules.hh"
#include "gdef.hh"
#include "mast.hh"
#include "mval.hh"
#include "mtype.hh"
#include "shared-enums.hh"

namespace monomorphizer::printing {

    static void print_exp(mast::ExpID exp_id) {
        std::cout << exp_id << "/";
        if (exp_id == mast::NULL_NODE_ID) {
            std::cout << "<NULL_NODE_ID>";
        } else {
            mast::NodeKind nk = mast::get_node_kind(exp_id);
            switch (nk) {
                case mast::EXP_UNIT: { std::cout << "EXP_UNIT"; break; }
                case mast::EXP_INT: { std::cout << "EXP_INT"; break; }
                case mast::EXP_FLOAT: { std::cout << "EXP_FLOAT"; break; }
                case mast::EXP_STRING: { std::cout << "EXP_STRING"; break; }
                case mast::EXP_LID: { std::cout << "EXP_LID"; break; }
                case mast::EXP_GID: { std::cout << "EXP_GID"; break; }
                case mast::EXP_FUNC_CALL: { std::cout << "EXP_FUNC_CALL"; break; }
                case mast::EXP_UNARY_OP: { std::cout << "EXP_UNARY_OP"; break; }
                case mast::EXP_BINARY_OP: { std::cout << "EXP_BINARY_OP"; break; }
                case mast::EXP_IF_THEN_ELSE: { std::cout << "EXP_IF_THEN_ELSE"; break; }
                case mast::EXP_GET_TUPLE_FIELD: { std::cout << "EXP_GET_TUPLE_FIELD"; break; }
                case mast::EXP_GET_POLY_MODULE_FIELD: { std::cout << "EXP_GET_POLY_MODULE_FIELD"; break; }
                case mast::EXP_GET_MONO_MODULE_FIELD: { std::cout << "EXP_GET_MONO_MODULE_FIELD"; break; }
                case mast::EXP_LAMBDA: { std::cout << "EXP_LAMBDA"; break; }
                case mast::EXP_ALLOCATE_ONE: { std::cout << "EXP_ALLOCATE_ONE"; break; }
                case mast::EXP_ALLOCATE_MANY: { std::cout << "EXP_ALLOCATE_MANY"; break; }
                case mast::EXP_CHAIN: { std::cout << "EXP_CHAIN"; break; }
                default: { std::cout << "<!!ERROR_EXP:nk=" << (size_t)nk << ">"; break; }
            }
        }
    }
    static void print_ts(mast::TypeSpecID ts_id) {
        std::cout << ts_id << "/";
        if (ts_id == mast::NULL_NODE_ID) {
            std::cout << "<NULL_NODE_ID>";
        } else {
            mast::NodeKind nk = mast::get_node_kind(ts_id);
            switch (nk) {
                case mast::TS_UNIT: { std::cout << "TS_UNIT"; } break;
                case mast::TS_GID: { std::cout << "TS_GID"; } break;
                case mast::TS_LID: { std::cout << "TS_LID"; } break;
                case mast::TS_PTR: { std::cout << "TS_PTR"; } break;
                case mast::TS_ARRAY: { std::cout << "TS_ARRAY"; } break;
                case mast::TS_SLICE: { std::cout << "TS_SLICE"; } break;
                case mast::TS_FUNC_SGN: { std::cout << "TS_FUNC_SGN"; } break;
                case mast::TS_TUPLE: { std::cout << "TS_TUPLE"; } break;
                case mast::TS_GET_POLY_MODULE_FIELD: { std::cout << "TS_GET_POLY_MODULE_FIELD"; } break;
                case mast::TS_GET_MONO_MODULE_FIELD: { std::cout << "TS_GET_MONO_MODULE_FIELD"; } break;
                default: { std::cout << "<!!ERROR_TS:nk=" << (size_t)nk << ">"; } break;
            }
        }
    }
    static void print_val(mval::ValueID val_id) {
        if (val_id == mval::NULL_VID) {
            std::cout << "<NULL_VID>";
        } else {
            std::cout << val_id;

            mval::ValueKind vk = mval::value_kind(val_id);
            
            std::cout << "/";
            switch (vk) {
                case mval::VK_ERROR: { std::cout << "TK_ERROR"; } break;
                case mval::VK_S8: { std::cout << "VK_S8"; } break;
                case mval::VK_S16: { std::cout << "VK_S16"; } break;
                case mval::VK_S32: { std::cout << "VK_S32"; } break;
                case mval::VK_S64: { std::cout << "VK_S64"; } break;
                case mval::VK_U1: { std::cout << "VK_U1"; } break;
                case mval::VK_U8: { std::cout << "VK_U8"; } break;
                case mval::VK_U16: { std::cout << "VK_U16"; } break;
                case mval::VK_U32: { std::cout << "VK_U32"; } break;
                case mval::VK_U64: { std::cout << "VK_U64"; } break;
                case mval::VK_F32: { std::cout << "VK_F32"; } break;
                case mval::VK_F64: { std::cout << "VK_F64"; } break;
                case mval::VK_STRING: { std::cout << "VK_STRING"; } break;
                case mval::VK_TUPLE: { std::cout << "VK_TUPLE"; } break;
                case mval::VK_FUNCTION: { std::cout << "VK_FUNCTION"; } break;
                default: { std::cout << "<!!ERROR_VID:vk=" << (size_t)vk << ">"; } break;
            }

            auto vi = mval::value_info(val_id);
            switch (vk) {
                case mval::VK_S8: { std::cout << "=" << vi.s8; } break;
                case mval::VK_S16: { std::cout << "=" << vi.s16; } break;
                case mval::VK_S32: { std::cout << "=" << vi.s32; } break;
                case mval::VK_S64: { std::cout << "=" << vi.s64; } break;
                case mval::VK_U1: { std::cout << "=" << vi.u1; } break;
                case mval::VK_U8: { std::cout << "=" << vi.u8; } break;
                case mval::VK_U16: { std::cout << "=" << vi.u16; } break;
                case mval::VK_U32: { std::cout << "=" << vi.u32; } break;
                case mval::VK_U64: { std::cout << "=" << vi.u64; } break;
                case mval::VK_F32: { std::cout << "=" << vi.f32; } break;
                case mval::VK_F64: { std::cout << "=" << vi.f64; } break;
                
                default: { std::cout << "=(...)"; } break;
            }
        }
    }
    static void print_type(mtype::TID type_id) {
        if (type_id == UNIVERSAL_NULL_ID) {
            std::cout << "<NULL_TID>";
        } else {
            std::cout << type_id;

            mtype::TypeKind tk = mtype::kind_of_tid(type_id);

            std::cout << "/";
            switch (tk) {
                case mtype::TK_ERROR: { std::cout << "TK_ERROR"; } break;
                case mtype::TK_UNIT: { std::cout << "TK_UNIT"; } break;
                case mtype::TK_U1: { std::cout << "TK_U1"; } break;
                case mtype::TK_U8: { std::cout << "TK_U8"; } break;
                case mtype::TK_U16: { std::cout << "TK_U16"; } break;
                case mtype::TK_U32: { std::cout << "TK_U32"; } break;
                case mtype::TK_U64: { std::cout << "TK_U64"; } break;
                case mtype::TK_S8: { std::cout << "TK_S8"; } break;
                case mtype::TK_S16: { std::cout << "TK_S16"; } break;
                case mtype::TK_S32: { std::cout << "TK_S32"; } break;
                case mtype::TK_S64: { std::cout << "TK_S64"; } break;
                case mtype::TK_F32: { std::cout << "TK_F32"; } break;
                case mtype::TK_F64: { std::cout << "TK_F64"; } break;
                case mtype::TK_STRING: { std::cout << "TK_STRING"; } break;
                case mtype::TK_TUPLE: { std::cout << "TK_TUPLE"; } break;
                case mtype::TK_POINTER: { std::cout << "TK_POINTER"; } break;
                case mtype::TK_ARRAY: { std::cout << "TK_ARRAY"; } break;
                case mtype::TK_SLICE: { std::cout << "TK_SLICE"; } break;
                case mtype::TK_FUNCTION: { std::cout << "TK_FUNCTION"; } break;
                default: { std::cout << "<!!ERROR_TID:tk=" << tk << ">"; } break;
            }
        }
    }
    static void print_def_id(GDefID def_id) {
        auto def_name = gdef::get_def_name(def_id);
        std::cout << def_name << ": DefID=" << def_id << ", ";
        if (def_id == gdef::NULL_GDEF_ID) {
            std::cout << "<NULL_DEF_ID>";
        } else {
            switch (gdef::get_def_kind(def_id)) {
                case gdef::DefKind::BV_EXP: {std::cout << "BV_EXP";} break;
                case gdef::DefKind::BV_TS: {std::cout << "BV_TS";} break;
                case gdef::DefKind::CONST_EXP: {
                    std::cout << "CONST_EXP=";
                    print_exp(gdef::get_def_target(def_id));
                } break;
                case gdef::DefKind::CONST_TS: {
                    std::cout << "CONST_TS=";
                    print_ts(gdef::get_def_target(def_id));
                } break;
                case gdef::DefKind::CONST_TOT_VAL: {
                    std::cout << "CONST_TOT_VAL=";
                    print_val(gdef::get_def_target(def_id));
                } break;
                case gdef::DefKind::CONST_TOT_TID: {
                    std::cout << "CONST_TOT_TID=";
                    print_type(gdef::get_def_target(def_id));
                } break;
            }
        }
    }
    void print_mono_mod(MonoModID mono_mod_id) {
        auto mod_name = modules::get_mono_mod_name(mono_mod_id);
        std::cout << "\t" "MonoMod(" << mono_mod_id << "): " << mod_name << std::endl;
        size_t field_count = modules::get_mono_mod_field_count(mono_mod_id);
        for (size_t field_index = 0; field_index < field_count; field_index++) {
            GDefID field_def_id = modules::get_mono_mod_field_at(mono_mod_id, field_index);
            std::cout << "\t" "- ";
            print_def_id(field_def_id);
            std::cout << std::endl;
        }
    }
    void print_poly_mod(PolyModID poly_mod_id) {
        auto mod_name = modules::get_poly_mod_name(poly_mod_id);
        std::cout << "\t" "PolyMod(" << poly_mod_id << "): " << mod_name << std::endl;

        size_t formal_arg_count = modules::get_poly_mod_formal_arg_count(poly_mod_id);
        for (size_t formal_arg_index = 0; formal_arg_index < formal_arg_count; formal_arg_index++) {
            GDefID formal_arg_def_id = modules::get_poly_mod_formal_arg_at(poly_mod_id, formal_arg_index);
            std::cout << "\t" "- ";
            print_def_id(formal_arg_def_id);
            std::cout << std::endl;
        }

        size_t field_count = modules::get_poly_mod_field_count(poly_mod_id);
        for (size_t field_index = 0; field_index < field_count; field_index++) {
            GDefID field_def_id = modules::get_poly_mod_field_at(poly_mod_id, field_index);
            std::cout << "\t" "- ";
            print_def_id(field_def_id);
            std::cout << std::endl;
        }
    }

}