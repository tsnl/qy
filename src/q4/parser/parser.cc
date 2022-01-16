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

#include "q4/ast/ast.hh"
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
    antlrcpp::Any visitFile(Q4SourceFileParser::FileContext* context) override;
    antlrcpp::Any visitStmt(Q4SourceFileParser::StmtContext* context) override;
    antlrcpp::Any visitBindStmt(Q4SourceFileParser::BindStmtContext* context) override;
    antlrcpp::Any visitEvalStmt(Q4SourceFileParser::EvalStmtContext* context) override;
    antlrcpp::Any visitImportStmt(Q4SourceFileParser::ImportStmtContext* context) override;
    antlrcpp::Any visitImplStmt(Q4SourceFileParser::ImplStmtContext* context) override;
    antlrcpp::Any visitDeclareStmt(Q4SourceFileParser::DeclareStmtContext* context) override;
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
    PExp newExp = q4::newAstNode<LiteralStringExp>(m_source, span(context), std::move(m_tmpRuneBuf));
    m_tmpRuneBuf = std::vector<int>();
    return newExp;
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
    else if (context->declare) { return visitDeclareStmt(context->declare); }
    else {
        panic("NotImplemented: constructing an unknown stmt: %s", context->getText().c_str());
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
antlrcpp::Any Q4SfParser::visitDeclareStmt(Q4SourceFileParser::DeclareStmtContext* context) {

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
antlrcpp::Any Q4SfParser::visitWrappedExpr(Q4SourceFileParser::WrappedExprContext* context) {

}
antlrcpp::Any Q4SfParser::visitPrimaryExpr(Q4SourceFileParser::PrimaryExprContext* context) {

}
antlrcpp::Any Q4SfParser::visitLiteralExpr(Q4SourceFileParser::LiteralExprContext* context) {

}
antlrcpp::Any Q4SfParser::visitParenExpr(Q4SourceFileParser::ParenExprContext* context) {

}
antlrcpp::Any Q4SfParser::visitChainExpr(Q4SourceFileParser::ChainExprContext* context) {

}
antlrcpp::Any Q4SfParser::visitLambdaExpr(Q4SourceFileParser::LambdaExprContext* context) {

}
antlrcpp::Any Q4SfParser::visitAdtTSE(Q4SourceFileParser::AdtTSEContext* context) {

}
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