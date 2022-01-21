#pragma once

#include <array>
#include <vector>
#include <string>
#include <cstdint>

#include "q4/util/intern.hh"
#include "node.hh"
#include "loc.hh"

// core:
namespace q4 {
    class BaseNode;
    class BaseStmt;
    class BaseExp;

    using PNode = BaseNode*;
    using PStmt = BaseStmt*;
    using PExp = BaseExp*;
}

// base node:
namespace q4 {
    class BaseNode {
    private:
        Span m_span;
    protected:
        BaseNode(Span span);
    public:
        BaseFileLoc* loc(Source* source) const { return new FileSpanLoc(source, m_span); }
    };
    class BaseStmt: public BaseNode {
    protected:
        BaseStmt(Span span);
    };
    class BaseExp: public BaseNode {
    protected:
        BaseExp(Span span);
    };
}

// expression helpers:
namespace q4 {
    struct FormalArg { 
        IntStr name; PExp tse; Span span; 
        FormalArg(IntStr name, PExp tse, Span span);
    };
    enum class UnaryOperator { 
        Mut, LogicalNot, BitwiseNot, Pos, Neg, DeRef
    };
    enum class BinaryOperator { 
        Mul, Div, Rem, 
        Add, Sub, 
        Is, IsNot, 
        GThan, LThan, GEq, LEq, Eq, NEq, 
        BitwiseXOr, BitwiseAnd, BitwiseOr, 
        LogicalAnd, LogicalOr 
    };
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
    enum class AdtKind {
        Struct, Union
    };
}

// expressions:
namespace q4 {
    struct LiteralNoneExp: public BaseExp { 
    public:
        LiteralNoneExp(Span span); 
    };
    class BaseLiteralBoolExp: public BaseExp {
    protected:
        BaseLiteralBoolExp(Span span);
        virtual ~BaseLiteralBoolExp() = default;
    public:
        bool is_t() const;
        bool is_f() const;
    };
    struct TLiteralBoolExp: public BaseLiteralBoolExp { 
        TLiteralBoolExp(Span span); 
    };
    struct FLiteralBoolExp: public BaseLiteralBoolExp { 
        FLiteralBoolExp(Span span); 
    };
    class LiteralSymbolExp: public BaseExp {
    private:
        IntStr m_symbolCode;
    public:
        LiteralSymbolExp(Span span, IntStr symbolCode);
    };
    class LiteralIntExp: public BaseExp {
    private:
        unsigned long long m_mantissa;
        std::string m_rawText;
        std::string m_cleanText;
        LiteralIntFlags m_flags;
    public:
        LiteralIntExp(Span span, std::string rawText, int base);
    };
    class LiteralRealExp: public BaseExp {
    private:
        long double m_approx;
        std::string m_text;
        LiteralRealFlags m_flags;
    public:
        LiteralRealExp(Span span, std::string text);
    };
    class LiteralStringExp: public BaseExp {
    public:
        LiteralStringExp(Span span, std::vector<int> runes);
    };
    class UnitRefExp: public BaseExp {
    public:
        UnitRefExp(Span span);
    };
    class ThisRefExp: public BaseExp {
    public:
        ThisRefExp(Span span);
    };
    class IdRefExp: public BaseExp {
    private:
        IntStr m_name;
    public:
        IdRefExp(Span span, IntStr name);
    };
    class ChainExp: public BaseExp {
    private:
        std::vector<PStmt> m_prefix;
        PExp m_optTail;
    public:
        ChainExp(Span span, std::vector<PStmt>&& prefix, PExp optTail);
    };
    class BaseLambdaExp: public BaseExp {
    private:
        std::vector<FormalArg> m_args;
        PExp m_body;
    public:
        BaseLambdaExp(Span span, std::vector<FormalArg> args, PExp body);
    };
    struct LambdaExp: public BaseLambdaExp { 
        LambdaExp(Span span, std::vector<FormalArg> args, PExp body); 
    };
    struct AotLambdaExp: public BaseLambdaExp { 
        AotLambdaExp(Span span, std::vector<FormalArg> args, PExp body); 
    };
    class SignatureTSE: public BaseExp {
    private:
        std::vector<PExp> m_args;
        PExp m_ret_type;
    public:
        SignatureTSE(Span span, std::vector<PExp> args, PExp ret_type);
    };
    class AdtTSE: public BaseExp {
    private:
        AdtKind m_adtKind;
        std::vector<FormalArg> m_fields;
    public:
        AdtTSE(Span span, AdtKind adtKind, std::vector<FormalArg> fields);
    };
    class InterfaceTSE: public BaseExp {
    public:
        enum class ReqSpecKind { NonStatic, Static, Env };
        enum class ProSpecKind { NonStatic, Static };
        class ReqSpec: BaseNode { 
            friend InterfaceTSE;
        private:
            ReqSpecKind kind; 
            IntStr name; 
            PExp tse; 
        public:
            ReqSpec(Span span, ReqSpecKind kind, IntStr name, PExp tse);
        };
        class ProSpec: BaseNode { 
            friend InterfaceTSE;
        private:
            ProSpecKind kind; 
            IntStr name; 
            PExp tse; 
        public:
            ProSpec(Span span, ProSpecKind kind, IntStr name, PExp tse);
        };
        class Header: BaseNode {
            friend InterfaceTSE;
        private:
            std::vector<ReqSpec> reqs;
            std::vector<ProSpec> pros;
        private:
            Header(
                Span span, 
                std::vector<ReqSpec> reqs, 
                std::vector<ProSpec> pros
            );
        };
    private:
        Header m_header;
        std::vector<PStmt> m_body;
    public:
        InterfaceTSE(Span span, Header header, std::vector<PStmt> body);
    };
    class IteExp: public BaseExp {
    private:
        PExp m_cond;
        PExp m_thenBranch;
        PExp m_optElseBranch;
    public:
        IteExp(Span span, PExp cond, PExp thenBranch, PExp optElseBranch = nullptr);
    };
    class BaseBuiltinOpExp: public BaseExp {};
    struct SizeBuiltinOpExp: public BaseBuiltinOpExp { SizeBuiltinOpExp(Span span, PExp operand); };
    struct TypeBuiltinOpExp: public BaseBuiltinOpExp { TypeBuiltinOpExp(Span span, PExp operand); };
    
    class BaseInvokeExp: public BaseExp {
    private:
        PExp m_msgReceiver;
        std::vector<PExp> m_args;
    public:
        BaseInvokeExp(Span span, PExp msgReceiver, std::vector<PExp> args);
    };
    struct LookupExp: public BaseInvokeExp { 
        LookupExp(Span span, PExp msgReceiver, std::vector<PExp> args); 
    };
    struct CallExp: public BaseInvokeExp { 
        CallExp(Span span, PExp msgReceiver, std::vector<PExp> args); 
    };
    struct InitExp: public BaseInvokeExp { 
        InitExp(Span span, PExp msgReceiver, std::vector<PExp> args); 
    };
    class DotExp: public BaseExp {
    private:
        PExp m_container;
        IntStr m_key;
    public:
        DotExp(Span span, PExp container, IntStr key);
    };
    class UnaryExp: public BaseExp {
    private:
        UnaryOperator m_operator;
        PExp m_operand;
    public:
        UnaryExp(UnaryOperator uop, PExp operand);
    };
    class BinaryExp: public BaseExp {
    private:
        BinaryOperator m_operator;
        PExp m_ltOperand;
        PExp m_rtOperand;
    public:
        BinaryExp(BinaryOperator bop, PExp ltOperand, PExp rtOperand);
    };
}

// statements:
namespace q4 {
    enum class BindStmtKind {
        EnvTos,
        Static,
        NonStatic
    };
    class BindStmt: public BaseStmt {
    private:
        BindStmtKind m_kind;
        IntStr m_name;
        PExp m_initializer;
    public:
        BindStmt(Span span, BindStmtKind kind, IntStr name, PExp initializer);
    };
    class EvalStmt: public BaseStmt {
    private:
        PExp m_evalExp;
    public:
        EvalStmt(Span span, PExp evalExp);
    };
    class ImportStmt: public BaseStmt {
    private:
        std::string m_path;
    public:
        ImportStmt(Span span, std::string path);
    };
    class ImplStmt: public BaseStmt {
    private:
        PExp m_t;
        PExp m_ifc;
        std::vector<PStmt> m_implBody;
    public:
        ImplStmt(Span span, PExp t, PExp ifc, std::vector<PStmt> implBody);
    };
}