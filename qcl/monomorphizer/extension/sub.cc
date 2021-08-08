#include "sub.hh"

#include <map>

#include "defs.hh"
#include "debug.hh"

namespace monomorphizer::sub {

    size_t const DEFAULT_SUBSTITUTION_CAPACITY = 1024;

    class Substitution {
      private:
        std::map<DefID, DefID> m_subs;

      public:
        Substitution();

      public:
        void add_monomorphizing_replacement(
            DefID original_def_id, 
            DefID replacement_def_id
        );
        DefID rw_def_id(
            DefID def_id
        );
      private:
        static bool validate_monomorphizing_replacement(
            DefID original_def_id,
            DefID replacement_def_id
        );
    };

    Substitution::Substitution()
    :   m_subs()
    {}

    void Substitution::add_monomorphizing_replacement(
        DefID original_def_id,
        DefID replacement_def_id
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
        assert(old_pair.first == m_subs.end());
    }

    bool Substitution::validate_monomorphizing_replacement(
        DefID original_def_id,
        DefID replacement_def_id
    ) { 
        // checking replacement def kind: no BV allowed or non-tot consts
        defs::DefKind replacement_def_kind = defs::get_def_kind(
            replacement_def_id
        );
        switch (replacement_def_kind) {
            case defs::DefKind::CONST_TOT_TID: 
            case defs::DefKind::CONST_TOT_VAL: {
                // replacement must be a total constant so our replacement does
                // not include any free variables.
            } break;

            default: {
                return false;
            };
        }

        // checking original def kind: only BV allowed.
        defs::DefKind original_def_kind = defs::get_def_kind(
            original_def_id
        );
        switch (original_def_kind) {
            case defs::DefKind::BV_EXP:
            case defs::DefKind::BV_TS: {
                // replacement must be a bound var
            } break;

            default: {
                return false;
            };
        }

        // all OK
        return true;
    }

    DefID Substitution::rw_def_id(DefID def_id) {
        auto it = m_subs.find(def_id);
        if (it == m_subs.end()) {
            return def_id;
        } else {
            return it->second;
        }
    }

}

namespace monomorphizer::sub {

    void add_monomorphizing_replacement(
        Substitution* sub, 
        DefID original_def_id, DefID replacement_def_id
    ) {
        sub->add_monomorphizing_replacement(
            original_def_id, 
            replacement_def_id
        );
    }

    DefID rw_def_id(Substitution* sub, DefID def_id) {
        return sub->rw_def_id(def_id);
    }

}