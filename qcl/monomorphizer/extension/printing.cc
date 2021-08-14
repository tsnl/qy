#include "printing.hh"

#include <iostream>
#include <iomanip>

#include "modules.hh"
#include "defs.hh"

namespace monomorphizer::printing {

    void print_def_id(DefID def_id) {
        auto def_name = defs::get_def_name(def_id);
        std::cout << def_name << " (" << def_id << "): ";
        switch (defs::get_def_kind(def_id)) {
            case defs::DefKind::BV_EXP: {std::cout << "BV_EXP";} break;
            case defs::DefKind::BV_TS: {std::cout << "BV_TS";} break;
            case defs::DefKind::CONST_EXP: {std::cout << "CONST_EXP";} break;
            case defs::DefKind::CONST_TS: {std::cout << "CONST_TS";} break;
            case defs::DefKind::CONST_TOT_VAL: {std::cout << "CONST_TOT_VAL";} break;
            case defs::DefKind::CONST_TOT_TID: {std::cout << "CONST_TOT_TID";} break;
        }
    }
    void print_mono_mod(MonoModID mono_mod_id) {
        auto mod_name = modules::get_mono_mod_name(mono_mod_id);
        std::cout << "MonoMod: " << mod_name << std::endl;
        size_t field_count = modules::get_mono_mod_field_count(mono_mod_id);
        for (size_t field_index = 0; field_index < field_count; field_index++) {
            DefID field_def_id = modules::get_mono_mod_field_at(mono_mod_id, field_index);
            std::cout << "- ";
            print_def_id(field_def_id);
            std::cout << std::endl;
        }
    }
    void print_poly_mod(PolyModID poly_mod_id) {
        auto mod_name = modules::get_poly_mod_name(poly_mod_id);
        std::cout << "Polymod: " << mod_name << std::endl;
        size_t field_count = modules::get_poly_mod_field_count(poly_mod_id);
        for (size_t field_index = 0; field_index < field_count; field_index++) {
            DefID field_def_id = modules::get_poly_mod_field_at(poly_mod_id, field_index);
            std::cout << "- ";
            print_def_id(field_def_id);
            std::cout << std::endl;
        }
    }

}