#include "vm.impl.hh"

namespace qcl {

    IntStr VM_Impl::intern(char const* null_terminated_bytes) {
        std::string const key{null_terminated_bytes};
        auto existing_it = m_interned_str_map.find(key);
        if (existing_it != m_interned_str_map.end()) {
            return existing_it->second;
        } else {
            IntStr new_id = 1 + m_interned_str_map.size();
            m_interned_str_map.insert({key, new_id});
            return new_id;
        }
    }

}
