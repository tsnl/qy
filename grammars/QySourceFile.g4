grammar QySourceFile;

options {
    language = 'Python3';
}

fragment L: [a-z] ;
fragment U: [A-Z] ;
fragment D: [0-9] ;
fragment H: [0-9a-fA-F] ;
TID: ('_'*) (U (L|D|'_')*) ;
VID: ('_'*) (L (L|D|'_')*) ;
LIT_DEC_INT: ('+'|'-')? D+ ;
LIT_HEX_INT: ('+'|'-')? '0x' H+ ;
LIT_FLOAT: LIT_DEC_INT '.' LIT_DEC_INT ('f')? ;

LINE_COMMENT: '//' (~'\n')*? -> channel(HIDDEN);
BLOCK_COMMENT: '/*' (.|BLOCK_COMMENT)*? '*/' -> channel(HIDDEN);

sourceFile
    : unwrappedBlock EOF
    ;

block
    : '{' unwrappedBlock '}'
    ;
unwrappedBlock
    : (statements+=statement ';')*
    ;

statement
    : bind1vStatement
    | bind1fStatement
    | bind1tStatement
    | type1vStatement
    | constStatement
    | iteStatement
    | useStatement
    ;
bind1vStatement
    : TID '=' expression
    ;
bind1fStatement
    : TID '(' csIdentifierList ')' '=' expression
    ;
bind1tStatement
    : TID '=' typeSpec
    ;
type1vStatement
    : VID ':' typeSpec
    ;
constStatement
    : 'const' block
    ;
iteStatement
    : 'if' cond=expression then_body=block ('else' (elif_stmt=iteStatement | else_body=unwrappedBlock))?
    ;
useStatement
    : 'use' vid=VID
    | 'use' tid=TID
    ;

expression
    : binaryExpression
    ;
primaryExpression
    : lit_integer                   #litIntPrimaryExpression
    | lit_float                     #litFloatPrimaryExpression
    | 'iota'                        #iotaPrimaryExpression
    | VID                           #vidPrimaryExpression
    | TID                           #rttidPrimaryExpression
    | '(' through=expression ')'    #parenPrimaryExpression
    ;
postfixExpression
    : through=primaryExpression
    | fn=postfixExpression '(' (args+=expression)* ')'
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
    : signatureTypeSpec
    ;
primaryTypeSpec
    : TID
    ;
adtTypeSpec
    : through=primaryTypeSpec
    | kw=('struct'|'union') b=block
    ;
signatureTypeSpec
    : through=adtTypeSpec
    | '(' (argTypeSpecs+=funcArgTypeSpec)* ')' op='->' ret=signatureTypeSpec
    ;
funcArgTypeSpec
    : typeSpec
    | VID ':' typeSpec
    ;

lit_integer
    : LIT_DEC_INT
    | LIT_HEX_INT
    ;
lit_float
    : LIT_FLOAT
    ;
csIdentifierList
    : ids+=TID (',' ids+=TID)*
    ;
