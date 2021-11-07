grammar QySourceFile;

options {
    language = 'Python3';
}

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

TID: (U (L|U|D|'_')*) ;
VID: ((L|'_') (L|U|D|'_')*) ;
LIT_DEC_INT: ('+'|'-')?      D+ IS? ;
LIT_HEX_INT: ('+'|'-')? '0x' H+ IS? ;
LIT_FLOAT: LIT_DEC_INT '.' LIT_DEC_INT FS? ;
LIT_SQ_STRING: ('\'' (ANY_ESC|'\\\''|~[\r\n\\'])*?  '\'');
LIT_DQ_STRING: ('"'  (ANY_ESC|'\\"' |~[\r\n\\"])*?  '"');
LIT_ML_DQ_STRING: '"""' (.)*? '"""';
LIT_ML_SQ_STRING: '\'\'\'' (.)*? '\'\'\'';

LINE_COMMENT: '//' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' (BLOCK_COMMENT|.)*? '*/' -> skip;
WHITESPACE: ('\n'|'\r'|'\t'|' ') -> skip;

sourceFile
    : unwrapped_block=unwrappedBlock EOF
    ;

block
    : '{' unwrapped_block=unwrappedBlock '}'
    ;
unwrappedBlock
    : (statements+=statement ';')*
    ;

statement
    : b1v=bind1vStatement
    | b1f=bind1fStatement
    | b1t=bind1tStatement
    | t1v=type1vStatement
    | con=constStatement
    | ite=iteStatement
    | ret=returnStatement
    ;
bind1vStatement
    : name=VID '=' initializer=expression
    ;
bind1fStatement
    : name=VID '(' args=csVIdList ')' '=' body_exp=expression
    | name=VID '(' args=csVIdList ')' '{' body_block=unwrappedBlock '}'
    ;
bind1tStatement
    : name=TID '=' initializer=typeSpec
    ;
type1vStatement
    : (is_pub='export')? name=VID ':' ts=typeSpec
    ;
constStatement
    : 'const' b=block
    ;
iteStatement
    : 'if' cond=expression then_body=block ('else' (elif_stmt=iteStatement | else_body=block))?
    ;
returnStatement
    : 'return' ret_exp=expression
    ;

expression
    : through=binaryExpression
    ;
primaryExpression
    : litInteger                    #litIntPrimaryExpression
    | litFloat                      #litFloatPrimaryExpression
    | litString                     #litStringPrimaryExpression
    | 'iota'                        #iotaPrimaryExpression
    | id_tok=VID                    #vidPrimaryExpression
    | '(' through=expression ')'    #parenPrimaryExpression
/*  | 'rtti' '(' typeSpec ')'       #rttiPrimaryExpression */
    ;
postfixExpression
    : through=primaryExpression                             #throughPostfixExpression
    | proc=postfixExpression '(' args=csExpressionList ')'  #procCallExpression
    | made_ts=typeSpec '(' args=csExpressionList ')'        #constructorExpression
    | container=postfixExpression '.' key=VID               #dotIdExpression
    ;
unaryExpression
    : through=postfixExpression             #throughUnaryExpression
    | op=unaryOperator e=unaryExpression    #unaryOpExpression
    ;
unaryOperator
    : '*'
    | 'not'
    | '-'
    | '+'
    ;
binaryExpression
    : through=logicalOrExpression
    ;
multiplicativeExpression
    : through=unaryExpression
    | lt=multiplicativeExpression op=('*'|'/'|'%') rt=unaryExpression
    ;
additiveExpression
    : through=multiplicativeExpression
    | lt=additiveExpression op=('+'|'-') rt=multiplicativeExpression
    ;
shiftExpression
    : through=additiveExpression
    | lt=shiftExpression op=('<<'|'>>') rt=additiveExpression
    ;
relationalExpression
    : through=shiftExpression
    | lt=relationalExpression op=('<'|'>'|'<='|'>=') rt=shiftExpression
    ;
equalityExpression
    : through=relationalExpression
    | lt=equalityExpression op=('=='|'!=') rt=relationalExpression
    ;
andExpression
    : through=equalityExpression
    | lt=andExpression '&' rt=equalityExpression
    ;
xorExpression
    : through=andExpression
    | lt=xorExpression '^' rt=andExpression
    ;
orExpression
    : through=xorExpression
    | lt=orExpression '|' rt=xorExpression
    ;
logicalAndExpression
    : through=orExpression
    | lt=logicalAndExpression op=('and'|'&&') rt=orExpression
    ;
logicalOrExpression
    : through=logicalAndExpression
    | lt=logicalOrExpression op=('or'|'||') rt=logicalAndExpression
    ;

typeSpec
    : through=signatureTypeSpec
    ;
primaryTypeSpec
    : id_tok=TID
    | tok='float32'
    | tok='float64'
    | tok='int64'
    | tok='int32'
    | tok='int16'
    | tok='int8'
    | tok='uint64'
    | tok='uint32'
    | tok='uint16'
    | tok='uint8'
    | tok='bool'
    | tok='void'
    ;
adtTypeSpec
    : through=primaryTypeSpec
    | kw=('struct'|'union') '{' args=csFormalArgSpecList '}'
    ;
signatureTypeSpec
    : through=adtTypeSpec
    | '(' args=csFormalArgSpecList ')' '=>' ret=signatureTypeSpec
    ;
formalArgSpec
    : ts=typeSpec
    | name_tok=VID ':' ts=typeSpec
    ;

litInteger: deci=LIT_DEC_INT | hexi=LIT_HEX_INT;
litFloat: tok=LIT_FLOAT;
litString: (pieces+=(LIT_SQ_STRING | LIT_DQ_STRING | LIT_ML_SQ_STRING | LIT_ML_DQ_STRING))+;
csVIdList: ids+=VID (',' ids+=VID)* ;
csFormalArgSpecList: specs+=formalArgSpec (',' specs+=formalArgSpec)* ;
csExpressionList: exps+=expression (',' exps+=expression)* ;
