// This grammar is purely for documentation, but should be kept up-to-date.
// If the parser diverges from this grammar, this grammar should be taken as the
// source of truth.

grammar Qy;

tokens {
  INDENT, DEDENT, EOL, SEMICOLON,
  VID, TID,
  LITERAL
} 

sourceFile: topLevelStatement+ ;

//
// Statements
//

topLevelStatement: suiteStatement | multilineBindFunctionStatement | bindTypeStatement ;
suiteStatement: unilineSuiteStatement | multilineSuiteStatement ;
extendStatement: multilineBindFunctionStatement | multilineBindPropertyStatement ;

unilineSuiteStatement: simpleSuiteStatement (';' simpleSuiteStatement)* EOL ;
simpleSuiteStatement: unilineBindValueStatement | unilineControlFlowStatement ;
unilineBindValueStatement: valuePattern '=' unilineTerm ;
unilineControlFlowStatement: unilineBreakStatement | unilineReturnStatement | unilineContinueStatement ;
unilineBreakStatement: 'break' unilineTerm? ;
unilineReturnStatement: 'return' unilineTerm? ;
unilineContinueStatement: 'continue' ;

bindTypeStatement: TID ('[' csTypeFormalArgList ']')? '=' bindTypeInitializer ;
bindTypeInitializer: typeExpr EOL | EOL INDENT typeExpr DEDENT ;

multilineSuiteStatement: multilineBindValueStatement | multilineLoopStatement ;
multilineBindValueStatement: valuePattern '=' multilineTerm ;
multilineLoopStatement: multilineForStatement | multilineWhileDoStatement | multilineDoWhileStatement ;
multilineForStatement: 'for' valuePattern 'in' unilineTerm 'do' suiteTerm ;
multilineWhileDoStatement: 'while' unilineTerm 'do' suiteTerm EOL ;
multilineDoWhileStatement: 'do' suiteTerm 'while' unilineTerm EOL ;

multilineBindFunctionStatement: VID '(' csValueFormalArgList? ')' '=' (unilineTerm EOL | multilineTerm) ;
multilineBindPropertyStatement: valueFormalArg '=' propertyDefBlock ;
propertyDefBlock: EOL INDENT (propertyVerb '->' (unilineTerm EOL | multilineTerm))+ ;
propertyVerb: 'get' | 'set' ;

//
// Terms
//

unilineTerm: binaryTerm ;

primaryTerm: (namePrefix)? VID | LITERAL | listTerm | dictionaryTerm | parenTerm ;
listTerm: '[' csTermList ']' ;
dictionaryTerm: '{' csDictionaryPairList '}' ;
dictionaryPair: unilineTerm ':' unilineTerm ;
parenTerm: '(' unilineTerm ')' ;

postfixTerm: primaryTerm postfixTermSuffix? ;
postfixTermSuffix
  : '(' csTermList ')'
  | '[' unilineTerm ']'
  | '.' VID '(' csTermList ')'
  | '.' VID
  ;

unaryTerm: postfixTerm | unaryOp unaryTerm ;
unaryOp: '&' 'mut'? 'weak'? | '+' | '-' | '*' | '!' ;

binaryTerm: orLogicalBinaryTerm ;
mulBinaryTerm: unaryTerm | mulBinaryTerm mulBinaryOp unaryTerm ;
addBinaryTerm: mulBinaryTerm | addBinaryTerm addBinaryOp mulBinaryTerm;
shiftBinaryTerm: addBinaryTerm | shiftBinaryTerm shiftBinaryOp addBinaryTerm ;
relBinaryTerm: shiftBinaryTerm | relBinaryTerm relBinaryOp shiftBinaryTerm ;
eqBinaryTerm: relBinaryTerm | eqBinaryTerm eqBinaryOp relBinaryTerm ;
xorBitwiseBinaryTerm: eqBinaryTerm | xorBitwiseBinaryTerm xorBitwiseBinaryOp eqBinaryTerm ;
andBitwiseBinaryTerm: xorBitwiseBinaryTerm | andBitwiseBinaryTerm andBitwiseBinaryOp xorBitwiseBinaryTerm ;
orBitwiseBinaryTerm: andBitwiseBinaryTerm | orBitwiseBinaryTerm orBitwiseBinaryOp andBitwiseBinaryTerm ;
andLogicalBinaryTerm: orBitwiseBinaryTerm | andLogicalBinaryTerm andLogicalBinaryOp orBitwiseBinaryTerm ;
orLogicalBinaryTerm: andLogicalBinaryTerm | orLogicalBinaryTerm orLogicalBinaryTerm andLogicalBinaryTerm ;

mulBinaryOp: '*' | '/' | '//' | '%' ;
addBinaryOp: '+' | '-' ;
shiftBinaryOp: '<<' | '>>' ;
relBinaryOp: '<' | '>' | '<=' | '>=' ;
eqBinaryOp: '==' | '!=' ;
xorBitwiseBinaryOp: '^' ;
andBitwiseBinaryOp: '&' ;
orBitwiseBinaryOp: '|' ;
andLogicalBinaryOp: '&&' ;
orLogicalBinaryOp: '||' ;

multilineTerm: suiteTerm | multilineIteTerm ;
suiteTerm: EOL INDENT suiteStatement+ DEDENT ;
multilineIteTerm: 'if' unilineTerm 'then' suiteTerm ('elif' unilineTerm 'then' suiteTerm)* ('else' suiteTerm)? ;

//
// Types
//

typeSpec: (namePrefix)? TID ('[' csTemplateActualArgList ']')? ;
templateActualArg: unilineTerm | typeSpec ;

typeExpr: sumTypeExpr ;
mulTypeExpr: typeSpec | '{' csValueFormalArgList '}' ;
sumTypeExpr: mulTypeExpr ('|' mulTypeExpr)+ ;

//
// Patterns, misc
//

valuePattern: valueFormalArg | '(' csValueFormalArgList ')' ;
valueFormalArg: VID (':' typeSpec)? ;

typeFormalArg: TID | valueFormalArg ;

namePrefix: (TID '.')+ ;

//
// Lists
//

csValueFormalArgList: valueFormalArg (',' valueFormalArg)* ;
csTypeFormalArgList: typeFormalArg (',' typeFormalArg)* ;
csTemplateActualArgList: templateActualArg (',' templateActualArg)* ;
csTermList: unilineTerm (',' unilineTerm)* ;
csDictionaryPairList: dictionaryPair (',' dictionaryPair)* ;
