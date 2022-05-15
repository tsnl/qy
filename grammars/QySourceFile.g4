grammar QySourceFile;

options {
    language = 'Python3';
}

sourceFile
    : (statements+=statement ';')* EOF
    ;

block
    : '{' unwrapped_block=unwrappedBlock '}'
    ;
unwrappedBlock
    : (prefix_statements+=statement ';')* 
    ;
constBlock
    : '{' (bindings+=bind1vTerm ';')* '}'
    ;

statement
    : b1v=bind1vStatement
    | b1f=bind1fStatement
    | b1t=bind1tStatement
    | t1v=type1vStatement
    | con=constStatement
    | ret=returnStatement
    | discard=discardStatement
    | loop=loopStatement
    | 'test' ID '=' ID macroArgBlock
    ;
bind1vStatement
    : 'val' b1v_term=bind1vTerm
    ;
bind1fStatement
    : 'def' name=ID '(' args=csDefArgSpecList ')' (':' opt_ret_ts=typeSpec)? '=' body_exp=expression
    ;
bind1tStatement: 'type' name=ID '=' initializer=typeSpec ;
type1vStatement: ((is_pub='pub')|'pvt') name=ID ':' ts=typeSpec ;
constStatement: 'const' ':' type_spec=typeSpec b=constBlock ;
returnStatement: 'return' ret_exp=expression ;
discardStatement: 'eval' discarded_exp=expression ;
loopStatement
    : while_do='while' cond=expression 'do' body=block
    | do_while='do' body=block 'while' cond=expression 
    ;

bind1vTerm
    : name=ID '=' initializer=expression
    ;

expression: through=binaryExpression ;
primaryExpression
    : litBoolean                                                                            #litBoolPrimaryExpression
    | litInteger                                                                            #litIntPrimaryExpression
    | litFloat                                                                              #litFloatPrimaryExpression
    | litString                                                                             #litStringPrimaryExpression
    | 'pred!'                                                                               #prevConstPrimaryExpression
    | id_tok=ID                                                                             #idPrimaryExpression
    | '(' through=expression ')'                                                            #parenPrimaryExpression
    | lam=lambdaExpression                                                                  #lambdaPrimaryExpression
    | 'if' '(' cond=expression ')' then=lambdaExpression ('else' else_=lambdaExpression)?   #itePrimaryExpression
/*  | 'rtti' '(' typeSpec ')'       #rttiPrimaryExpression */
    ;
lambdaExpression
    : '{' ('(' opt_arg_names=csIdList ')' ('=>'|no_closure='->'))? 
        prefix=unwrappedBlock (opt_tail=expression)? '}'
    ;
postfixExpression
    : through=primaryExpression                                       #throughPostfixExpression
    | proc=postfixExpression '(' args=csExpressionList ')'            #procCallExpression
    | (kw='new'|(kw='push'|kw='heap') (is_mut='mut')?) 
        made_ts=typeSpec '(' args=csExpressionList ')'                #constructorExpression
    | container=postfixExpression '.' key=ID                          #dotIdExpression
    | container=postfixExpression '.' 'get' '(' index=expression ')'  #indexExpression
    | container=postfixExpression '.' 'ptr' '(' index=expression ')'  #indexRefExpression
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
    | 'do'
    ;
binaryExpression
    : through=updateExpression
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
updateExpression
    : through=logicalOrExpression
    | lt=updateExpression op=':=' rt=logicalOrExpression
    ;


typeSpec
    : through=signatureTypeSpec
    ;
primaryTypeSpec
    : id_tok=ID
    | tok='F32'
    | tok='F64'
    | tok='I64'
    | tok='I32'
    | tok='I16'
    | tok='I8'
    | tok='U64'
    | tok='U32'
    | tok='U16'
    | tok='U8'
    | tok='Bool'
    | tok='Void'
    | tok='String'
    ;
adtTypeSpec
    : through=primaryTypeSpec               #throughAdtTypeSpec
    | '{' args=csTypeArgSpecList '}'      #unionAdtTypeSpec
    | '(' args=csTypeArgSpecList ')'      #tupleAdtTypeSpec
    ;
ptrTypeSpec
    : through=adtTypeSpec
    | ptrName='Ptr'    '[' pointee=ptrTypeSpec ']'
    | ptrName='MutPtr' '[' pointee=ptrTypeSpec ']'
    ;
arrayTypeSpec
    : through=ptrTypeSpec
    | tok='Array'       '[' elem_ts=typeSpec ',' count=expression ']'
    | tok='MutArray'    '[' elem_ts=typeSpec ',' count=expression ']'
    | tok='ArrayBox'    '[' elem_ts=typeSpec ']'
    | tok='MutArrayBox' '[' elem_ts=typeSpec ']'
    ;
signatureTypeSpec
    : through=arrayTypeSpec
    | '(' args=csTypeArgSpecList ')' ('->'|has_closure_slot='=>') ret=signatureTypeSpec
    ;

typeArgSpec
    : ts=typeSpec
    | name_tok=ID ':' ts=typeSpec
    ;
defArgSpec
    : name_tok=ID
    | name_tok=ID ':' ts=typeSpec
    ;

macroArgBlock
    : '[' (mab=macroArgBlock | ident=ID | exp=expression | ts=typeSpec)+? ']'
    ;

litBoolean: is_true='true' | 'false';
litInteger: deci=LIT_DEC_INT | hexi=LIT_HEX_INT;
litFloat: tok=LIT_FLOAT;
litString: (pieces+=(LIT_SQ_STRING | LIT_DQ_STRING | LIT_ML_SQ_STRING | LIT_ML_DQ_STRING))+;
csIdList: (ids+=ID (',' ids+=ID)*)? ;

csTypeArgSpecList: (specs+=typeArgSpec (',' specs+=typeArgSpec)*)? ;
csDefArgSpecList: (specs+=defArgSpec (',' specs+=defArgSpec)*)? ;
csExpressionList: (exps+=expression (',' exps+=expression)*)? ;

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
fragment BASIC_ID: ((L|'_') (L|D|'_')*) ;

MACRO_ID: BASIC_ID '!';
ID: BASIC_ID;
LIT_DEC_INT:      D+ IS? ;
LIT_HEX_INT: '0x' H+ IS? ;
LIT_FLOAT: LIT_DEC_INT '.' LIT_DEC_INT FS? ;
LIT_SQ_STRING: ('\'' (ANY_ESC|'\\\''|~[\r\n\\'])*?  '\'');
LIT_DQ_STRING: ('"'  (ANY_ESC|'\\"' |~[\r\n\\"])*?  '"');
LIT_ML_DQ_STRING: '"""' (.)*? '"""';
LIT_ML_SQ_STRING: '\'\'\'' (.)*? '\'\'\'';

LINE_COMMENT: '//' ~[\r\n]* -> skip;
BLOCK_COMMENT: '/*' (BLOCK_COMMENT|.)*? '*/' -> skip;
WHITESPACE: ('\n'|'\r'|'\t'|' ') -> skip;
