#include "printing.hh"

#include <iostream>
#include <iomanip>

#include "modules.hh"
#include "gdef.hh"
#include "mast.hh"
#include "mval.hh"
#include "mtype.hh"

namespace monomorphizer::printing {

    static void print_exp(mast::ExpID exp_id) {
        std::cout << exp_id << "/";
        if (exp_id == mast::NULL_NODE_ID) {
            std::cout << "<NULL_NODE_ID>";
        } else {
            mast::NodeKind nk = mast::get_node_kind(exp_id);
            switch (nk) {
                case mast::NodeKind::EXP_UNIT: { std::cout << "EXP_UNIT"; break; }
                case mast::NodeKind::EXP_INT: { std::cout << "EXP_INT"; break; }
                case mast::NodeKind::EXP_FLOAT: { std::cout << "EXP_FLOAT"; break; }
                case mast::NodeKind::EXP_STRING: { std::cout << "EXP_STRING"; break; }
                case mast::NodeKind::EXP_LID: { std::cout << "EXP_LID"; break; }
                case mast::NodeKind::EXP_GID: { std::cout << "EXP_GID"; break; }
                case mast::NodeKind::EXP_FUNC_CALL: { std::cout << "EXP_FUNC_CALL"; break; }
                case mast::NodeKind::EXP_UNARY_OP: { std::cout << "EXP_UNARY_OP"; break; }
                case mast::NodeKind::EXP_BINARY_OP: { std::cout << "EXP_BINARY_OP"; break; }
                case mast::NodeKind::EXP_IF_THEN_ELSE: { std::cout << "EXP_IF_THEN_ELSE"; break; }
                case mast::NodeKind::EXP_GET_TUPLE_FIELD: { std::cout << "EXP_GET_TUPLE_FIELD"; break; }
                case mast::NodeKind::EXP_GET_POLY_MODULE_FIELD: { std::cout << "EXP_GET_POLY_MODULE_FIELD"; break; }
                case mast::NodeKind::EXP_GET_MONO_MODULE_FIELD: { std::cout << "EXP_GET_MONO_MODULE_FIELD"; break; }
                case mast::NodeKind::EXP_LAMBDA: { std::cout << "EXP_LAMBDA"; break; }
                case mast::NodeKind::EXP_ALLOCATE_ONE: { std::cout << "EXP_ALLOCATE_ONE"; break; }
                case mast::NodeKind::EXP_ALLOCATE_MANY: { std::cout << "EXP_ALLOCATE_MANY"; break; }
                case mast::NodeKind::EXP_CHAIN: { std::cout << "EXP_CHAIN"; break; }
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
                case mast::NodeKind::TS_UNIT: { std::cout << "TS_UNIT"; break; }
                case mast::NodeKind::TS_GID: { std::cout << "TS_GID"; break; }
                case mast::NodeKind::TS_LID: { std::cout << "TS_LID"; break; }
                case mast::NodeKind::TS_PTR: { std::cout << "TS_PTR"; break; }
                case mast::NodeKind::TS_ARRAY: { std::cout << "TS_ARRAY"; break; }
                case mast::NodeKind::TS_SLICE: { std::cout << "TS_SLICE"; break; }
                case mast::NodeKind::TS_FUNC_SGN: { std::cout << "TS_FUNC_SGN"; break; }
                case mast::NodeKind::TS_TUPLE: { std::cout << "TS_TUPLE"; break; }
                case mast::NodeKind::TS_GET_POLY_MODULE_FIELD: { std::cout << "TS_GET_POLY_MODULE_FIELD"; break; }
                case mast::NodeKind::TS_GET_MONO_MODULE_FIELD: { std::cout << "TS_GET_MONO_MODULE_FIELD"; break; }
                default: { std::cout << "<!!ERROR_TS:nk=" << (size_t)nk << ">"; break; }
            }
        }
    }
    static void print_val(mval::ValueID val_id) {
        std::cout << "<placeholder-value>";
        // todo: implement me
    }
    static void print_type(mtype::TID type_id) {
        std::cout << "<placeholder-type>";
        // todo: implement me
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
        std::cout << "MonoMod: " << mod_name << std::endl;
        size_t field_count = modules::get_mono_mod_field_count(mono_mod_id);
        for (size_t field_index = 0; field_index < field_count; field_index++) {
            GDefID field_def_id = modules::get_mono_mod_field_at(mono_mod_id, field_index);
            std::cout << "- ";
            print_def_id(field_def_id);
            std::cout << std::endl;
        }
    }
    void print_poly_mod(PolyModID poly_mod_id) {
        auto mod_name = modules::get_poly_mod_name(poly_mod_id);
        std::cout << "PolyMod: " << mod_name << std::endl;

        size_t formal_arg_count = modules::get_poly_mod_formal_arg_count(poly_mod_id);
        for (size_t formal_arg_index = 0; formal_arg_index < formal_arg_count; formal_arg_index++) {
            GDefID formal_arg_def_id = modules::get_poly_mod_formal_arg_at(poly_mod_id, formal_arg_index);
            std::cout << "- ";
            print_def_id(formal_arg_def_id);
            std::cout << std::endl;
        }

        size_t field_count = modules::get_poly_mod_field_count(poly_mod_id);
        for (size_t field_index = 0; field_index < field_count; field_index++) {
            GDefID field_def_id = modules::get_poly_mod_field_at(poly_mod_id, field_index);
            std::cout << "- ";
            print_def_id(field_def_id);
            std::cout << std::endl;
        }
    }

}