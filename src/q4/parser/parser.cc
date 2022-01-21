#include "q4/parser/parser.hh"

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "antlr4-runtime.h"
#include "Q4SourceFileLexer.h"
#include "Q4SourceFileParser.h"
#include "Q4SourceFileBaseVisitor.h"

#include "q4/ast/node.hh"
#include "q4/ast/source.hh"
#include "q4/util/feedback.hh"

namespace q4 {

class Q4SfParser: private Q4SourceFileBaseVisitor {
  private:
    Source* m_source;
    std::vector<int> m_tmpRuneBuf;
  public:
    Q4SfParser(Source* source);
  public:
    std::vector<PStmt> parseSourceFile();
  private:
    Span span(antlr4::ParserRuleContext* ctx) const;
  private:  // scans character codes into 'm_tmpRuneBuf'
    void helpScanSingleLineStringLiteral(antlr4::Token* token, char quoteChar);
    void helpScanMultiLineStringLiteral(antlr4::Token* token, char quoteChar);
  private:
    antlrcpp::Any visitStringLiteralChunk(Q4SourceFileParser::StringLiteralChunkContext* context) override;
    antlrcpp::Any visitStringLiteral(Q4SourceFileParser::StringLiteralContext* context) override;
    antlrcpp::Any visitFormalArg(Q4SourceFileParser::FormalArgContext* context) override;
    antlrcpp::Any visitFile(Q4SourceFileParser::FileContext* context) override;
    antlrcpp::Any visitStmt(Q4SourceFileParser::StmtContext* context) override;
    antlrcpp::Any visitBindStmt(Q4SourceFileParser::BindStmtContext* context) override;
    antlrcpp::Any visitEvalStmt(Q4SourceFileParser::EvalStmtContext* context) override;
    antlrcpp::Any visitImportStmt(Q4SourceFileParser::ImportStmtContext* context) override;
    antlrcpp::Any visitImplStmt(Q4SourceFileParser::ImplStmtContext* context) override;
    antlrcpp::Any visitUnwrappedImplBody(Q4SourceFileParser::UnwrappedImplBodyContext* context) override;
    antlrcpp::Any visitImplBodyStmt(Q4SourceFileParser::ImplBodyStmtContext* context) override;
    antlrcpp::Any visitNonstaticImplBindStmt(Q4SourceFileParser::NonstaticImplBindStmtContext* context) override;
    antlrcpp::Any visitStaticImplBindStmt(Q4SourceFileParser::StaticImplBindStmtContext* context) override;
    antlrcpp::Any visitExpr(Q4SourceFileParser::ExprContext* context) override;
    antlrcpp::Any visitWrappedExpr(Q4SourceFileParser::WrappedExprContext* context) override;
    antlrcpp::Any visitPrimaryExpr(Q4SourceFileParser::PrimaryExprContext* context) override;
    antlrcpp::Any visitLiteralExpr(Q4SourceFileParser::LiteralExprContext* context) override;
    antlrcpp::Any visitParenExpr(Q4SourceFileParser::ParenExprContext* context) override;
    antlrcpp::Any visitChainExpr(Q4SourceFileParser::ChainExprContext* context) override;
    antlrcpp::Any visitLambdaExpr(Q4SourceFileParser::LambdaExprContext* context) override;
    antlrcpp::Any visitAdtTSE(Q4SourceFileParser::AdtTSEContext* context) override;
    antlrcpp::Any visitInterfaceTSE(Q4SourceFileParser::InterfaceTSEContext* context) override;
    antlrcpp::Any visitInterfaceHeader(Q4SourceFileParser::InterfaceHeaderContext* context) override;
    antlrcpp::Any visitInterfaceProvisionSpecForNonStatic(Q4SourceFileParser::InterfaceProvisionSpecForNonStaticContext* context) override;
    antlrcpp::Any visitInterfaceProvisionSpecForStatic(Q4SourceFileParser::InterfaceProvisionSpecForStaticContext* context) override;
    antlrcpp::Any visitIteExpr(Q4SourceFileParser::IteExprContext* context) override;
    antlrcpp::Any visitSlicePostfixExpr(Q4SourceFileParser::SlicePostfixExprContext *ctx) override;
    antlrcpp::Any visitLookupPostfixExpr(Q4SourceFileParser::LookupPostfixExprContext *ctx) override;
    antlrcpp::Any visitInitializerPostfixExpr(Q4SourceFileParser::InitializerPostfixExprContext *ctx) override;
    antlrcpp::Any visitThroughPostfixExpr(Q4SourceFileParser::ThroughPostfixExprContext *ctx) override;
    antlrcpp::Any visitCallPostfixExpr(Q4SourceFileParser::CallPostfixExprContext *ctx) override;
    antlrcpp::Any visitDotPostfixExpr(Q4SourceFileParser::DotPostfixExprContext *ctx) override;
    antlrcpp::Any visitUnaryExpr(Q4SourceFileParser::UnaryExprContext *ctx) override;
    antlrcpp::Any visitMulBinaryExpr(Q4SourceFileParser::MulBinaryExprContext *ctx) override;
    antlrcpp::Any visitAddBinaryExpr(Q4SourceFileParser::AddBinaryExprContext *ctx) override;
    antlrcpp::Any visitTypingBinaryExpr(Q4SourceFileParser::TypingBinaryExprContext *ctx) override;
    antlrcpp::Any visitCmpBinaryExpr(Q4SourceFileParser::CmpBinaryExprContext *ctx) override;
    antlrcpp::Any visitBitwiseXOrBinaryExpr(Q4SourceFileParser::BitwiseXOrBinaryExprContext *ctx) override;
    antlrcpp::Any visitBitwiseAndBinaryExpr(Q4SourceFileParser::BitwiseAndBinaryExprContext *ctx) override;
    antlrcpp::Any visitBitwiseOrBinaryExpr(Q4SourceFileParser::BitwiseOrBinaryExprContext *ctx) override;
    antlrcpp::Any visitLogicalAndBinaryExpr(Q4SourceFileParser::LogicalAndBinaryExprContext *ctx) override;
    antlrcpp::Any visitLogicalOrBinaryExpr(Q4SourceFileParser::LogicalOrBinaryExprContext *ctx) override;
    antlrcpp::Any visitBinaryExpr(Q4SourceFileParser::BinaryExprContext *ctx) override;
};

Q4SfParser::Q4SfParser(Source* source)
:   m_source(source),
    m_tmpRuneBuf()
{}

Span Q4SfParser::span(antlr4::ParserRuleContext* ctx) const {
    // FIXME: hacky, inefficient: check if '\n' in stop token by linear scan, and if not, add token length to end position
    Span span;
    antlr4::Token* startToken = ctx->getStart();
    antlr4::Token* stopToken = ctx->getStop();
    std::string stopTokenText = stopToken->getText();
    span.first.lineIx = startToken->getLine() - 1;
    span.first.colIx = startToken->getCharPositionInLine();
    span.last.lineIx = stopToken->getLine();
    span.last.colIx = stopToken->getCharPositionInLine() + ((stopTokenText.find('\n') != std::string::npos) ? stopTokenText.size() : 0);
    return span;
}

antlrcpp::Any Q4SfParser::visitStringLiteralChunk(Q4SourceFileParser::StringLiteralChunkContext* context) {
    antlr4::Token* optSqToken = context->sq;
    if (optSqToken) { helpScanSingleLineStringLiteral(optSqToken, '\''); return 1; }
    antlr4::Token* optDqToken = context->dq;
    if (optDqToken) { helpScanSingleLineStringLiteral(optDqToken, '"'); return 1; }
    antlr4::Token* optMlSqToken = context->mlSq;
    if (optMlSqToken) { helpScanSingleLineStringLiteral(optMlSqToken, '"'); return 1; }
    antlr4::Token* optMlDqToken = context->mlDq;
    if (optMlDqToken) { helpScanSingleLineStringLiteral(optMlDqToken, '"'); return 1; }
    panic("NotImplemented: visiting an unknown StringLiteral chunk: '%s'", context->getText().c_str());
    return 0;
}
void Q4SfParser::helpScanSingleLineStringLiteral(antlr4::Token* token, char quoteChar) {
    std::string text = token->getText();
    assert(text.front() == quoteChar && text.back() == quoteChar);
    bool prevCharWasStartOfEscapeSeq = false;
    for (size_t i = 0+1; i < text.size()-1; i++) {
        char ch = text[i];
        if (ch <= 0) {
            panic("NotImplemented: UTF-8 characters in string literals");
        }
        if (ch == '\\' && !prevCharWasStartOfEscapeSeq) {
            prevCharWasStartOfEscapeSeq = true;
        } else {
            prevCharWasStartOfEscapeSeq = false;
            if (prevCharWasStartOfEscapeSeq) {
                if (ch == quoteChar) { m_tmpRuneBuf.push_back(quoteChar); }
                else if (ch == '\\') { m_tmpRuneBuf.push_back('\\'); }
                else if (ch == '0') { m_tmpRuneBuf.push_back(0); }
                else if (ch == 'n') { m_tmpRuneBuf.push_back('\n'); }
                else if (ch == 'r') { m_tmpRuneBuf.push_back('\r'); }
                else if (ch == 't') { m_tmpRuneBuf.push_back('\t'); }
                else if (ch == 'a') { m_tmpRuneBuf.push_back('\a'); }
                else if (ch == 'v') { m_tmpRuneBuf.push_back('\v'); }
                else { 
                    warning("Invalid escape sequence: \\%c", ch);
                    m_tmpRuneBuf.push_back('\\');
                    m_tmpRuneBuf.push_back(ch);
                }
            } else {
                m_tmpRuneBuf.push_back(ch);
            }
        }
    }
}
void Q4SfParser::helpScanMultiLineStringLiteral(antlr4::Token* token, char quoteChar) {
    std::string text = token->getText();
    assert(text.front() == quoteChar && text.back() == quoteChar);
    bool prevCharWasStartOfEscapeSeq = false;
    for (size_t i = 0+3; i < text.size()-3; i++) {
        char ch = text[i];
        if (ch <= 0) {
            panic("NotImplemented: UTF-8 characters in string literals");
        }
        if (ch == '\\' && !prevCharWasStartOfEscapeSeq) {
            prevCharWasStartOfEscapeSeq = true;
        } else {
            prevCharWasStartOfEscapeSeq = false;
            if (prevCharWasStartOfEscapeSeq) {
                if (ch == '\\') { m_tmpRuneBuf.push_back('\\'); }
                else if (ch == '0') { m_tmpRuneBuf.push_back(0); }
                else if (ch == 'n') { m_tmpRuneBuf.push_back('\n'); }
                else if (ch == 'r') { m_tmpRuneBuf.push_back('\r'); }
                else if (ch == 't') { m_tmpRuneBuf.push_back('\t'); }
                else if (ch == 'a') { m_tmpRuneBuf.push_back('\a'); }
                else if (ch == 'v') { m_tmpRuneBuf.push_back('\v'); }
                else { 
                    warning("Invalid escape sequence: \\%c", ch);
                    m_tmpRuneBuf.push_back('\\');
                    m_tmpRuneBuf.push_back(ch);
                }
            } else {
                m_tmpRuneBuf.push_back(ch);
            }
        }
    }
}
antlrcpp::Any Q4SfParser::visitStringLiteral(Q4SourceFileParser::StringLiteralContext* context) {
    // scan runes in each chunk in succession into 'tmpRuneBuf':
    m_tmpRuneBuf.clear();
    for (auto chunkContext: context->chunks) {
        int ec = visitStringLiteralChunk(chunkContext).as<int>();
        assert(ec == 0 && "visitStringLiteralChunk failed");
    }
    PExp newExp = new q4::LiteralStringExp(span(context), std::move(m_tmpRuneBuf));
    m_tmpRuneBuf = std::vector<int>();
    return newExp;
}

antlrcpp::Any Q4SfParser::visitFormalArg(Q4SourceFileParser::FormalArgContext* context) {
    return FormalArg{
        intern(context->name->getText()), 
        visitExpr(context->tse).as<PExp>(), 
        span(context)
    };
}

antlrcpp::Any Q4SfParser::visitFile(Q4SourceFileParser::FileContext* context) {
    std::vector<PStmt> stmts;
    for (auto stmtContext: context->stmts) {
        auto stmt = visitStmt(stmtContext).as<PStmt>();
        stmts.push_back(stmt);
    }
    return stmts;
}
antlrcpp::Any Q4SfParser::visitStmt(Q4SourceFileParser::StmtContext* context) {
    if (context->bind) { return visitBindStmt(context->bind); }
    else if (context->eval) { return visitEvalStmt(context->eval); }
    else if (context->import_) { return visitImportStmt(context->import_); }
    else if (context->impl) { return visitImplStmt(context->impl); }
    else {
        panic("NotImplemented: constructing an unknown stmt: %s", context->getText().c_str());
        return nullptr;
    }
}
antlrcpp::Any Q4SfParser::visitBindStmt(Q4SourceFileParser::BindStmtContext* context) {
    
}
antlrcpp::Any Q4SfParser::visitEvalStmt(Q4SourceFileParser::EvalStmtContext* context) {

}
antlrcpp::Any Q4SfParser::visitImportStmt(Q4SourceFileParser::ImportStmtContext* context) {

}
antlrcpp::Any Q4SfParser::visitImplStmt(Q4SourceFileParser::ImplStmtContext* context) {

}
antlrcpp::Any Q4SfParser::visitUnwrappedImplBody(Q4SourceFileParser::UnwrappedImplBodyContext* context) {

}
antlrcpp::Any Q4SfParser::visitImplBodyStmt(Q4SourceFileParser::ImplBodyStmtContext* context) {

}
antlrcpp::Any Q4SfParser::visitNonstaticImplBindStmt(Q4SourceFileParser::NonstaticImplBindStmtContext* context) {

}
antlrcpp::Any Q4SfParser::visitStaticImplBindStmt(Q4SourceFileParser::StaticImplBindStmtContext* context) {

}

antlrcpp::Any Q4SfParser::visitExpr(Q4SourceFileParser::ExprContext* context) {

}
antlrcpp::Any Q4SfParser::visitPrimaryExpr(Q4SourceFileParser::PrimaryExprContext* context) {
    if (context->wrapped) { return visitWrappedExpr(context->wrapped); }
    if (context->lambda) { return visitLambdaExpr(context->lambda); }
    if (context->aotLambda) { return visitAotLambdaExpr(context->aotLambda); }
    if (context->signature) { return visitSignatureTSE(context->signature); }
    if (context->ite) { return visitIteExpr(context->ite); }
    if (context->adt) { return visitAdtTSE(context->adt); }
    if (context->ifc) { return visitInterfaceTSE(context->ifc); }
    if (context->builtinOp) { return visitBuiltinOpExpr(context->builtinOp); }
    throw std::runtime_error("PARSER: visitPrimaryExpr: unexpected context: " + context->getText());
}
antlrcpp::Any Q4SfParser::visitWrappedExpr(Q4SourceFileParser::WrappedExprContext* context) {
    if (context->id) { return new IdRefExp(span(context), intern(context->id->getText())); }
    if (context->kwThis) { return new ThisRefExp(span(context)); }
    if (context->literal) { return visitLiteralExpr(context->literal); }
    if (context->paren) { return visitParenExpr(context->paren); }
    if (context->chain) { return visitChainExpr(context->chain); }
    throw std::runtime_error("PARSER: visitWrappedExpr: unexpected context: " + context->getText());
}
antlrcpp::Any Q4SfParser::visitLiteralExpr(Q4SourceFileParser::LiteralExprContext* context) {
    if (context->litBoolT) { return new TLiteralBoolExp(span(context)); }
    if (context->litBoolF) { return new FLiteralBoolExp(span(context)); }
    if (context->litNone) { return new LiteralNoneExp(span(context)); }
    if (context->litDecReal) { return new LiteralRealExp(span(context), context->litDecReal->getText()); }
    if (context->litDecInt) { return new LiteralIntExp(span(context), context->litDecInt->getText(), 10); }
    if (context->litHexInt) { return new LiteralIntExp(span(context), context->litHexInt->getText(), 16); }
    if (context->litBinInt) { return new LiteralIntExp(span(context), context->litBinInt->getText(), 2); }
    if (context->litSymbol) { return new LiteralSymbolExp(span(context), intern(context->litSymbol->getText())); }
    if (context->litString) { return visitStringLiteral(context->litString); }
    throw std::runtime_error("PARSER: visitLiteralExpr: unexpected context: " + context->getText());
}
antlrcpp::Any Q4SfParser::visitParenExpr(Q4SourceFileParser::ParenExprContext* context) {
    return (context->optExpr) ?
        visitExpr(context->optExpr) :
        new UnitRefExp(span(context));
}
antlrcpp::Any Q4SfParser::visitChainExpr(Q4SourceFileParser::ChainExprContext* context) {
    std::vector<PStmt> prefix{context->prefix.size()};
    for (size_t i = 0; i < prefix.size(); i++) {
        prefix[i] = visitStmt(context->prefix[i]).as<PStmt>();
    }
    PExp optTailExp = context->optExpr ? visitExpr(context->optExpr).as<PExp>() : nullptr;
    return new ChainExp(span(context), std::move(prefix), optTailExp);
}
antlrcpp::Any Q4SfParser::visitLambdaExpr(Q4SourceFileParser::LambdaExprContext* context) {
    std::vector<FormalArg> args;
    args.resize(context->formalArgs.size());
    for (size_t iArg = 0; iArg < args.size(); iArg++) {
        auto formalArg = visitFormalArg(context->formalArgs[iArg]).as<FormalArg>();
        args.push_back(formalArg);
    }
    PExp body = visitExpr(context->body).as<PExp>();
    return new LambdaExp(span(context), std::move(args), body);
}
// todo: add support for aotLambdaExpr
// todo: add support for signatureTSE
antlrcpp::Any Q4SfParser::visitAdtTSE(Q4SourceFileParser::AdtTSEContext* context) {
    AdtKind adtKind;
    if (context->prod) { adtKind = AdtKind::Struct; }
    else if (context->sum) { adtKind = AdtKind::Union; }
    else { throw std::runtime_error("ERROR: visitAdtTSE: unknown prefix keyword: " + context->getText()); }
    
    std::vector<FormalArg> fields;
    fields.reserve(context->formalArgs.size());
    for (size_t iField = 0; iField < fields.size(); iField++) {
        auto formalArg = visitFormalArg(context->formalArgs[iField]).as<FormalArg>();
        fields.push_back(formalArg);
    }

    return new AdtTSE(span(context), adtKind, std::move(fields));
}
// todo: implement all below methods
antlrcpp::Any Q4SfParser::visitInterfaceTSE(Q4SourceFileParser::InterfaceTSEContext* context) {

}
antlrcpp::Any Q4SfParser::visitInterfaceHeader(Q4SourceFileParser::InterfaceHeaderContext* context) {

}
antlrcpp::Any Q4SfParser::visitInterfaceProvisionSpecForNonStatic(Q4SourceFileParser::InterfaceProvisionSpecForNonStaticContext* context) {

}
antlrcpp::Any Q4SfParser::visitInterfaceProvisionSpecForStatic(Q4SourceFileParser::InterfaceProvisionSpecForStaticContext* context) {

}
antlrcpp::Any Q4SfParser::visitIteExpr(Q4SourceFileParser::IteExprContext* context) {

}

std::vector<PStmt> Q4SfParser::parseSourceFile() {
    Source* source = Source::get(nullptr, "test_file.q4");
    std::ifstream f{source->path()};

    antlr4::ANTLRInputStream input{f};
    Q4SourceFileLexer lexer{&input};
    antlr4::CommonTokenStream tokens{&lexer};
    Q4SourceFileParser parser{&tokens};

    Q4SourceFileParser::FileContext* file = parser.file();
    std::vector<PStmt> stmts = this->visit(file).as<std::vector<PStmt>>();
    return stmts;
}

}