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
    ('\\u' H H H H)
    ('\\U' H H H H H H H H)
);
fragment IS: [uUlLsS]+ ;
fragment FS: [fFdD]+ ;

TID: ('_'*) (U (L|U|D|'_')*) ;
VID: ('_'*) (L (L|U|D|'_')*) ;
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
    : 'if' cond=expression then_body=block ('else' (elif_stmt=iteStatement | else_body=unwrappedBlock))?
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
    | VID                           #vidPrimaryExpression
    | '(' through=expression ')'    #parenPrimaryExpression
    ;
postfixExpression
    : through=primaryExpression
    | fn=postfixExpression '(' args=csExpressionList ')'
    | constructor=typeSpec '(' args=csExpressionList ')'
    | container=postfixExpression '.' key=VID
    ;
unaryExpression
    : through=postfixExpression
    | op=unaryOperator e=unaryExpression
    ;
unaryOperator
    : '*'
    | '&'
    | 'not'
    | '-'
    | '+'
    ;
binaryExpression
    : logicalOrExpression
    ;
multiplicativeExpression
    : through=unaryExpression
    | lt=multiplicativeExpression op=('*'|'/'|'//'|'%') rt=unaryExpression
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
    | logicalAndExpression op=('and'|'&&') orExpression
    ;
logicalOrExpression
    : through=logicalAndExpression
    | lt=logicalOrExpression op='or' rt=logicalAndExpression
    ;

typeSpec
    : through=signatureTypeSpec
    ;
primaryTypeSpec
    : TID           #idRefTypeSpec
    | 'float32'     #float32TypeSpec
    | 'float64'     #float64TypeSpec
    | 'int64'       #int64TypeSpec
    | 'int32'       #int32TypeSpec
    | 'int16'       #int16TypeSpec
    | 'int8'        #int8TypeSpec
    | 'uint64'      #uint64TypeSpec
    | 'uint32'      #uint32TypeSpec
    | 'uint16'      #uint16TypeSpec
    | 'uint8'       #uint8TypeSpec
    | 'bool'        #uint1TypeSpec
    ;
adtTypeSpec
    : through=primaryTypeSpec
    | kw=('struct'|'union') '{' args=csFormalArgSpecList '}'
    ;
signatureTypeSpec
    : through=adtTypeSpec
    | '(' args=csFormalArgSpecList ')' op='->' ret=signatureTypeSpec
    ;
formalArgSpec
    : typeSpec
    | VID ':' typeSpec
    ;

litInteger: deci=LIT_DEC_INT | hexi=LIT_HEX_INT;
litFloat: tok=LIT_FLOAT;
litString: sq=LIT_SQ_STRING | dq=LIT_DQ_STRING | mlsq=LIT_ML_SQ_STRING | mldq=LIT_ML_DQ_STRING;
csVIdList: ids+=VID (',' ids+=VID)* ;
csFormalArgSpecList: specs+=formalArgSpec (',' specs+=formalArgSpec)* ;
csExpressionList: exps+=expression (',' exps+=expression)* ;
