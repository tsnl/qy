#pragma once

#include "node.hh"
#include <vector>
#include <string>
#include <cstdint>

namespace q4 {
    using LiteralIntFlags = uint8_t;
    using LiteralRealFlags = uint8_t;
    enum class LiteralIntFlag: LiteralIntFlags { 
        Suffix_Unsigned=0x1, Suffix_Long=0x2, Suffix_Short=0x4, 
        Base_Decimal=0x8, Base_Hexadecimal=0x10, Base_Binary=0x20, 
        PreOp_SignedPos=0x40, PreOp_SignedNeg=0x80 
    };
    enum class LiteralRealFlag: LiteralRealFlags { 
        Suffix_Float32=0x1, Suffix_Float64=0x2 
    };

    class LiteralIntExp: public BaseExp {
      private:
        unsigned long long m_mantissa;
        std::string m_rawText;
        std::string m_cleanText;
        LiteralIntFlags m_flags;
      public:
        LiteralIntExp(Span span, std::string rawText, LiteralIntFlags flags);
    };
    class LiteralRealExp: public BaseExp {
      private:
        long double m_approx;
        std::string m_text;
        LiteralRealFlags m_flags;
      public:
        LiteralRealExp(Span span, std::string text, LiteralRealFlags flags);
    };
    class LiteralStringExp: public BaseExp {
      public:
        LiteralStringExp(Span span, std::vector<int> runes);
    };
    
}