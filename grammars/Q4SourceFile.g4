// For reference only: not an actual source file, some features simplified.

grammar Q4SourceFile;
options {
    language = 'Cpp';
}

fragment L: [a-zA-Z_] ;
fragment B: [01] ;
fragment D: [0-9] ;
fragment H: [0-9a-fA-F] ;
fragment ANY_ESC: (
    ('\\' ('\\' | 'n' | 'r' | 't')) |
    ('\\x' H H)
    ('\\u' H H H H)
    ('\\U' H H H H H H H H)
);
fragment IS: [uUlLsS]+ ;
fragment FS: [fFdD]+ ;

ID: L D* ;
LIT_BIN_INT: ('+'|'-')? '0b' B+ IS? ;
LIT_DEC_INT: ('+'|'-')?      D+ IS? ;
LIT_HEX_INT: ('+'|'-')? '0x' H+ IS? ;
LIT_DEC_REAL: (LIT_DEC_INT '.' LIT_DEC_INT FS?) | (LIT_DEC_INT FS);
LIT_SQ_STRING: ('\'' (ANY_ESC|'\\\''|~[\r\n\\'])*?  '\'');
LIT_DQ_STRING: ('"'  (ANY_ESC|'\\"' |~[\r\n\\"])*?  '"');
LIT_ML_SQ_STRING: '\'\'\'' (.)*? '\'\'\'';
LIT_ML_DQ_STRING: '"""' (.)*? '"""';

LINE_COMMENT: '//' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' (BLOCK_COMMENT|.)*? '*/' -> skip;
WHITESPACE: ('\n'|'\r'|'\t'|' ') -> skip;

stringLiteralChunk: sq=LIT_SQ_STRING | dq=LIT_DQ_STRING | mlSq=LIT_ML_SQ_STRING | mlDq=LIT_ML_DQ_STRING ;
stringLiteral: (chunks+=stringLiteralChunk)+ ;

file: EOF | (stmts+=stmt)+ EOF;

stmt: bind=bindStmt | eval=evalStmt | import_=importStmt | impl=implStmt | declare=declareStmt;
bindStmt: ID '=' expr ;
evalStmt: expr ;
importStmt: 'import' stringLiteral ;
implStmt: 'impl' expr ':' expr 'using' '(' 'this' ':' 'This' ')' '{' unwrappedImplBody '}';
declareStmt: (isPub='pub'|isPvt='pvt'|isLoc='local') ID ':' expr ;
staticImplBindStmt: 'This' '.' ID ':' expr;

// impl body:
unwrappedImplBody: (stmts+=implBodyStmt) ;
implBodyStmt: nonstaticImplBindStmt | staticImplBindStmt;
nonstaticImplBindStmt: 'this' '.' ID ':' expr;

expr: primaryExpr ;
wrappedExpr     // single-token, string, or '(...)' '{...}'
    : id=ID
    | kwSelf='self'
    | literal=literalExpr
    | paren=parenExpr
    | chain=chainExpr
    ;
primaryExpr
    : wrapped=wrappedExpr
    | lambda=lambdaExpr
    | ite=iteExpr
    | adt=adtTSE
    | ifc=interfaceTSE
    ;
literalExpr
    : litBoolT='true'
    | litBoolF='false'
    | litNone='none'
    | '#' litSymbol=ID
    | litBinInt=LIT_BIN_INT
    | litDecInt=LIT_DEC_INT
    | litHexInt=LIT_HEX_INT
    | litReal=LIT_DEC_REAL
    | litString=stringLiteral
    ;
parenExpr: '(' ')' | '(' optExpr=expr ')' ;
chainExpr: '{' '}' | '{' optExpr=expr '}' | '{' (prefix+=stmt ';')+ '}' | '{' (prefix+=stmt ';')+ optTail=expr '}';
lambdaExpr
    : argNames+=ID '=>' body=expr
    | '(' argNames+=ID ')' '=>' body=expr
    | '(' argNames+= ID (',' argNames+= ID) ')' '=>' body=expr
    | '(' ')' '=>' body=expr
    ;
adtTSE
    : (prod='struct'|sum='enum')
        '{' (names+=ID ':' inits+=expr (',' names+=ID ':' inits+=expr)*)? '}'
    ;
interfaceTSE: 'interface' '(' 'self' '::' 'Self' ')' '{' interfaceHeader ';' (interfaceBody+=stmt ';')* '}' ;
interfaceHeader: 'requires' '{' (reqs+=expr ';')* '}' 'for' '{' (provisions+=interfaceProvisionSpec ';')* '}';
interfaceProvisionSpec
    : 'self' '.' ID '::' expr   #interfaceProvisionSpecForNonStatic
    | 'Self' '.' ID '::' expr   #interfaceProvisionSpecForStatic
    ;
iteExpr: 'if' '(' condExpr=expr ')' thenBranchExpr=wrappedExpr ('else' optElseBranchExpr=wrappedExprOrIteExpr)? ;
wrappedExprOrIteExpr: wrapped=wrappedExpr | ite=iteExpr ;

// TODO: implement rest of grammar from example.
//  - unary, binary expressions are pretty straightforward, EXCEPT
//      - include 'mut' as a unary operator
//      - binary:
//          - support ':' as a binary expression, with special meaning in `interface` and `assert`
//          - support 'is' and 'is not' i.e. multiple tokens in binary operator.
//          - support '->' as a chaining operator (for function types)
//  - postfix expressions: '(...)', '[...]', and '{...}' accept arbitrary numbers of arguments, functors are a thing, constructors are just function calls
//      - NOTE: {...} postfix also invokes a message, builtins use it for array initialization

