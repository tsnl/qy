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
    : (prefix_statements+=statement ';')* (tail=expression)?
    ;

statement
    : b1v=bind1vStatement
    | b1f=bind1fStatement
    | b1t=bind1tStatement
    | t1v=type1vStatement
    | con=constStatement
    | ite=iteStatement
    | ret=returnStatement
    | discard=discardStatement
    | for_=forStatement
    | break_=breakStatement
    | continue_=continueStatement
    ;
bind1vStatement
    : ('val'|is_mut='var') name=ID '=' initializer=expression
    ;
bind1fStatement
    : 'def' name=ID '(' args=csIdList ')' '=' body_exp=expression
    | 'def' name=ID '(' args=csIdList ')' '=' body_block=block
    ;
bind1tStatement: 'typ' name=ID '=' initializer=typeSpec ;
type1vStatement: ((is_pub='pub')|'pvt') name=ID ':' ts=typeSpec ;
constStatement: 'const' type_spec=typeSpec b=block ;
iteStatement
    : 'if' cond=expression then_body=block ('else' (elif_stmt=iteStatement | else_body=block))?
    ;
returnStatement: 'return' ret_exp=expression ;
discardStatement: 'discard' discarded_exp=expression ;
forStatement: 'for' body=block ;
breakStatement: 'break' ;
continueStatement: 'continue' ;

expression: through=binaryExpression ;
primaryExpression
    : litBoolean                                                        #litBoolPrimaryExpression
    | litInteger                                                        #litIntPrimaryExpression
    | litFloat                                                          #litFloatPrimaryExpression
    | litString                                                         #litStringPrimaryExpression
    | '$predecessor'                                                    #prevConstPrimaryExpression
    | id_tok=ID                                                         #idPrimaryExpression
    | '(' through=expression ')'                                        #parenPrimaryExpression
    | 'mux' '(' cond=expression ')' then=block 'else' else_=block       #muxPrimaryExpression
/*  | 'rtti' '(' typeSpec ')'       #rttiPrimaryExpression */
    ;
postfixExpression
    : through=primaryExpression                             #throughPostfixExpression
    | proc=postfixExpression '(' args=csExpressionList ')'  #procCallExpression
    | 'make' made_ts=typeSpec '(' args=csExpressionList ')' #constructorExpression
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
    | tok='Str'
    ;
adtTypeSpec
    : through=primaryTypeSpec               #throughAdtTypeSpec
    | '{' args=csFormalArgSpecList '}'      #unionAdtTypeSpec
    | '(' args=csFormalArgSpecList ')'      #tupleAdtTypeSpec
    ;
ptrTypeSpec
    : through=adtTypeSpec
    | ptrName='UnsafePtr' '[' pointee=ptrTypeSpec ']'
    | ptrName='MutUnsafePtr' '[' pointee=ptrTypeSpec ']'
    ;
signatureTypeSpec
    : through=ptrTypeSpec
    // TODO: enable optional args list with 0-arg closure: need typer overhaul!
    // | ('(' args=csFormalArgSpecList ')')? ('->'|has_closure_slot='=>') ret=signatureTypeSpec
    | ('(' args=csFormalArgSpecList ')') ('->'|has_closure_slot='=>') ret=signatureTypeSpec
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
