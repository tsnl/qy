#pragma once

#include <cstdint>

#include "rtti.hh"

namespace qcl {

    //
    // Forward declarations:
    //

    class Value;
    class ExtraValueInfo;
    union Datum128;

    //
    // Type implementations:
    //

    union Datum128 {
        uint64_t u;
        int64_t s;
        float f32;
        double f64;
        void* p;
        struct {
            uint64_t len;
            void* ptr;
        } a;
    };

    class Value {
      private:
        Datum128 m_datum;
        uint64_t m_tid;
        ExtraValueInfo* m_more;

      protected:
        Value(Datum128 value, ExtraValueInfo* more);

      public:
        Datum128 const& datum() const { return m_datum; }
        uint64_t const tid() const { return m_tid; }
        ExtraValueInfo const* const more() const { return m_more; }

      public:
        static Value new_unknown();
        static Value new_const_u_int(uint64_t u, TID tid);
        static Value new_const_s_int(int64_t s, TID tid);
        static Value new_const_float32(float f32, TID tid);
        static Value new_const_float64(double f64, TID tid);
        static Value new_const_ptr(void* p, TID tid);
        static Value new_const_tuple(void* mem, TID tid);
        static Value new_const_array(void* mem, TID tid);
        static Value new_const_empty_slice(void* mem, uint64_t value, TID tid);

      // todo: implement basic methods for ALL above type-kinds, using dynamic
      //       type-checking + evaluation.
      public:
        
    };

}   // namespace qcl
