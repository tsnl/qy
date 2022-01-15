#include <iostream>

#include "antlr4-runtime.h"
#include "Q4SourceFileLexer.h"
#include "Q4SourceFileParser.h"
#include "Q4SourceFileBaseVisitor.h"

#include <fstream>

namespace q4 {

void testFunc() {
    std::ifstream f{"test_file.q4"};

    antlr4::ANTLRInputStream input{f};
    Q4SourceFileLexer lexer{&input};
    antlr4::CommonTokenStream tokens{&lexer};
    Q4SourceFileParser parser{&tokens};

    Q4SourceFileParser::FileContext* file = parser.file();
}

}