grammar QySourceFile;

options {
    language = 'Python3';
}

fragment L: [a-zA-Z] ;
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

ID: ((L|'_') (L|D|'_')*) ;
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
    : 'let' name=ID '=' initializer=expression
    ;
bind1fStatement
    : 'let' name=ID '(' args=csIdList ')' '=' body_exp=expression
    | 'let' name=ID '(' args=csIdList ')' '{' body_block=unwrappedBlock '}'
    ;
bind1tStatement
    : 'let' name=ID '=' initializer=typeSpec
    ;
type1vStatement
    : ((is_pub='pub')|'val') name=ID ':' ts=typeSpec
    ;
constStatement
    : 'const' type_spec=typeSpec b=block
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
    : litBoolean                    #litBoolPrimaryExpression
    | litInteger                    #litIntPrimaryExpression
    | litFloat                      #litFloatPrimaryExpression
    | litString                     #litStringPrimaryExpression
    | '$.prevConst'                 #prevConstPrimaryExpression
    | id_tok=ID                     #idPrimaryExpression
    | '(' through=expression ')'    #parenPrimaryExpression
/*  | 'rtti' '(' typeSpec ')'       #rttiPrimaryExpression */
    ;
postfixExpression
    : through=primaryExpression                             #throughPostfixExpression
    | proc=postfixExpression '(' args=csExpressionList ')'  #procCallExpression
    | 'new' made_ts=typeSpec '(' args=csExpressionList ')'  #constructorExpression
    | container=postfixExpression '.' key=ID                #dotIdExpression
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
    : id_tok=ID
    | tok='f32'
    | tok='f64'
    | tok='i64'
    | tok='i32'
    | tok='i16'
    | tok='i8'
    | tok='u64'
    | tok='u32'
    | tok='u16'
    | tok='u8'
    | tok='bool'
    | tok='void'
    | tok='str'
    ;
adtTypeSpec
    : through=primaryTypeSpec
    | kw=('struct'|'union') '{' args=csFormalArgSpecList '}'
    ;
ptrTypeSpec
    : through=adtTypeSpec
    | ptrChar='^' pointee=ptrTypeSpec
    | ptrChar='&' pointee=ptrTypeSpec
    ;
signatureTypeSpec
    : through=ptrTypeSpec
    | '(' args=csFormalArgSpecList ')' '=>' ret=signatureTypeSpec
    ;
formalArgSpec
    : ts=typeSpec
    | name_tok=ID ':' ts=typeSpec
    ;

litBoolean: is_true='true' | 'false';
litInteger: deci=LIT_DEC_INT | hexi=LIT_HEX_INT;
litFloat: tok=LIT_FLOAT;
litString: (pieces+=(LIT_SQ_STRING | LIT_DQ_STRING | LIT_ML_SQ_STRING | LIT_ML_DQ_STRING))+;
csIdList: (ids+=ID (',' ids+=ID)*)? ;
csFormalArgSpecList: (specs+=formalArgSpec (',' specs+=formalArgSpec)*)? ;
csExpressionList: (exps+=expression (',' exps+=expression)*)? ;
