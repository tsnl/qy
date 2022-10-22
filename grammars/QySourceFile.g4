grammar QySourceFile;

options {
  language = 'Python3';
}

module: (stmt ';')+ ;

stmt: useStmt | bindValStmt | bindTypeStmt | defMethodStmt | defMainStmt;
useStmt: 'use' modulePrefix;
bindValStmt: bound=pattern '=' rhs=expr ;
bindTypeStmt: bound=TID template_args_pattern=templateArgsPattern? '=' body=typeExpr ;
defMethodStmt: ts=TID '.' name=VID '(' args=csFormalArgList? ')' ;
defMainStmt: 'main' '(' args=csFormalArgList? ')' '=' body=expr ;

expr: binaryExpr ;
csExprList: items+=expr (',' items+=expr)* ;

primaryExpr: idRefExpr | literalExpr | ifElseExpr | forExpr | parenExpr | tupleExpr | chainExpr ;
idRefExpr: local_vid=VID | container=contentTypeSpec '.' extern_vid=VID ;
literalExpr: intLiteral | floatLiteral | charLiteral | stringLiteral ;
ifElseExpr: 'if' '(' cond=expr ')' then=chainExpr 'else' (else_=chainExpr | elif_=ifElseExpr) ;
forExpr: 'for' '(' key=pattern 'in' iterable=expr ')' body=chainExpr ;
parenExpr: '(' expr ')' ;
tupleExpr: '(' items+=expr ',' ')' | '(' items+=expr (',' items+=expr)+ ')' ;
chainExpr: '{' (prefix+=stmt ';')* tail=expr '}' ;

postfixExpr
  : through=primaryExpr                             #throughPostfixExpr
  | fn=postfixExpr '(' args=csExprList ','? ')'     #postfixCallExpr
  | container=postfixExpr '[' key=expr ']'          #postfixGetItemExpr
  ;

unaryExpr
  : through=postfixExpr
  | operator=unaryExprOp operand=unaryExpr
  ;
unaryExprOp: '*' | '!' | '~' ;

// TODO: finish this
// binaryExpr: logicalOrBinaryExpr ;
// mulBinaryExpr:  ;
// logicalAndBinaryExpr:  ;
// logicalOrBinaryExpr: logicalAndBinaryExpr | logicalOrBinaryExpr 'or' logicalAndBinaryExpr;

typeSpec: unaryTypeSpec ;
contentTypeSpec: postfixTypeSpec ;
primaryTypeSpec: prefix=modulePrefix? TID ;
postfixTypeSpec: template_instance=templateInstanceTypeSpec | through=primaryTypeSpec ;
templateInstanceTypeSpec: primaryTypeSpec '[' csTemplateArgList ','? ']' ;
unaryTypeSpec: through=postfixTypeSpec | operator=unaryTypeOp operand=unaryTypeSpec;
unaryTypeOp: '*';

templateArg: expr | typeSpec ;
csTemplateArgList: templateArg (',' templateArg)* ;

typeExpr: structTypeExpr | unionTypeExpr ;
structTypeExpr: '(' fields=csFormalArgList? ')' ;
unionTypeExpr: '{' arms=csUnionArmList ','? '}' ;
unionArm: TID '(' fields=csFormalArgList? ')' ;
csUnionArmList: unionArm (',' unionArm)* ;

templateArgsPattern: '[' csTemplateFormalArgList ','? ']' ;
templateFormalArg: tid=TID | vid=VID (':' vid_ts=typeSpec)? ;
csTemplateFormalArgList: args+=templateFormalArg (',' args+=templateFormalArg)* ;

pattern: singleton=formalArg | '(' many=csFormalArgList ','? ')' ;
formalArg: is_weak='weak'? is_mut='mut'? vid=VID (':' ts=typeSpec)? ;
csFormalArgList: args+=formalArg (',' args+=formalArg)* ;

modulePrefix: (mod_name_prefix+=TID '.')+ ;

intLiteral: decimal=LIT_DEC_INT | hexadecimal=LIT_HEX_INT;
floatLiteral: LIT_FLOAT ;
charLiteral: LIT_SQ_CHAR ;
stringLiteral: single_line=LIT_DQ_STRING | multiline=LIT_ML_DQ_STRING ;

fragment L: [a-z] ;
fragment U: [A-Z] ;
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

VID: '_'* (L|'_') (L|D|'_')* ;
TID: '_'* (U)     (L|D|'_')* ;
LIT_DEC_INT:      D+ IS? ;
LIT_HEX_INT: '0x' H+ IS? ;
LIT_FLOAT: LIT_DEC_INT '.' LIT_DEC_INT FS? ;
LIT_SQ_CHAR: ('\'' (ANY_ESC | '\\\'' | ~[\r\n\\']) '\'');
LIT_DQ_STRING: ('"' (ANY_ESC | '\\"' | ~[\r\n\\"])*? '"');
LIT_ML_DQ_STRING: '"""' (.)*? '"""';

LINE_COMMENT: '#' ~[\r\n]* -> skip;
WHITESPACE: ('\n'|'\r'|'\t'|' ') -> skip;
