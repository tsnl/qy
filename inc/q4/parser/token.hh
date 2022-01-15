#pragma once

namespace q4 {

    enum class TokenKind {
        _Eof,
        _Outdated,

        Id,
        Literal_StringChunk,
        Literal_Int,
        Literal_Float,
        Literal_Rune,
        Literal_Symbol,
        
        Kw_If,
        Kw_Else,
        Kw_Requires,
        Kw_For,
        Kw_Mut,
        Kw_And,
        Kw_Or,
        Kw_Is,
        Kw_Not,
        Kw_Impl,
        Kw_Using,
        Kw_Pub, Kw_Pvt, Kw_Local,
        
        LParen, RParen,
        LSqBrk, RSqBrk,
        LCyBrk, RCyBrk,
        HashTag,
        Period,
        Semicolon,
        Comma,
        Equal,
        Plus,
        Minus,
        ColonEqual,
        Colon,
        DblColon,
        DblEqual,
        Asterisk,
        DblAsterisk,
        FSlash,
        DblFSlash,
        Ampersand, Caret, Pipe
    };

}