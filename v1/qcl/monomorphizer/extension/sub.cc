#include "sub.hh"

#include <map>
#include <iostream>
#include <cassert>

#include "gdef.hh"
#include "debug.hh"

namespace monomorphizer::sub {

    size_t const DEFAULT_SUBSTITUTION_CAPACITY = 1024;

    class Substitution {
      private:
        std::map<GDefID, GDefID> m_subs;

      public:
        Substitution();

      public:
        void add_monomorphizing_replacement(
            GDefID original_def_id,
            GDefID replacement_def_id
        );
        GDefID rw_def_id(GDefID def_id);
      private:
        static bool validate_monomorphizing_replacement(
            GDefID original_def_id,
            GDefID replacement_def_id
        );

      public:
        void debug_print();
    };

    Substitution::Substitution()
    :   m_subs()
    {}

    void Substitution::add_monomorphizing_replacement(
        GDefID original_def_id,
        GDefID replacement_def_id
    ) {
        // validation:
#if (MONOMORPHIZER_DEBUG)
        bool validate_ok = validate_monomorphizing_replacement(
            original_def_id, 
            replacement_def_id
        );
        assert(validate_ok && "Invalid monomorphizing replacement");
#endif
        auto old_pair = m_subs.insert({original_def_id, replacement_def_id});
        assert(old_pair.second && "Insertion into sub-map failed");

// #if (MONOMORPHIZER_DEBUG)
//         std::cout 
//             << "added monomorphizing replacement: " 
//             << original_def_id << " -> " << replacement_def_id 
//             << std::endl;
//         std::cout.flush();
// #endif
    }

    bool Substitution::validate_monomorphizing_replacement(
        GDefID original_def_id,
        GDefID replacement_def_id
    ) { 
        // checking replacement def kind: no BV allowed or non-tot consts
        gdef::DefKind replacement_def_kind = gdef::get_def_kind(
            replacement_def_id
        );
        switch (replacement_def_kind) {
            case gdef::DefKind::CONST_TOT_TID:
            case gdef::DefKind::CONST_TOT_VAL: {
                // replacement must be a total constant so our replacement does
                // not include any free variables.
            } break;

            default: {
                return false;
            };
        }

        // checking original def kind: only BV allowed.
        gdef::DefKind original_def_kind = gdef::get_def_kind(
            original_def_id
        );
        switch (original_def_kind) {
            case gdef::DefKind::BV_EXP:
            case gdef::DefKind::BV_TS: {
                // replacement must be a bound var
            } break;

            default: {
                return false;
            };
        }

        // all OK
        return true;
    }

    GDefID Substitution::rw_def_id(GDefID def_id) {
        auto it = m_subs.find(def_id);
        if (it == m_subs.end()) {
            return def_id;
        } else {
            return it->second;
        }
    }

}

namespace monomorphizer::sub {

    Substitution* create() {
        return new sub::Substitution();
    }

    void destroy(Substitution* s) {
        delete s;
    }

    void add_monomorphizing_replacement(
        Substitution* sub, 
        GDefID original_def_id, GDefID replacement_def_id
    ) {
        sub->add_monomorphizing_replacement(
            original_def_id, 
            replacement_def_id
        );
    }

    GDefID rw_def_id(Substitution* sub, GDefID def_id) {
        return sub->rw_def_id(def_id);
    }

    void debug_print(sub::Substitution* s) {
        s->debug_print();
    }

    void Substitution::debug_print() {
        std::cout << "Sub (" << m_subs.size() << "):" << std::endl;
        for (auto it = m_subs.begin(); it != m_subs.end(); it++) {
            std::cout << "- " << it->first << " -> " << it->second << std::endl;
        }
    }

}