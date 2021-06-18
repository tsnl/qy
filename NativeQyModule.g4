grammar NativeQyModule;

options {
    language = 'Python3';
}

//
// Module definitions:
//

fileModule
    : (imports=moduleImports ';')? (exports=moduleExports ';')? (moduleDefs+=moduleDef ';')*
    ;

moduleImports
    : 'imports' '{' (lines+=importLine ';')* '}'
    ;
importLine
    : name=VID 'from' path=stringPrimaryExp
    ;

moduleExports
    : 'exports' '{' lines+=exportLine (',' lines+=exportLine)* '}'
    ;
exportLine
    : name=VID ':' '*'
    ;

moduleDef
    : 'mod' name=VID ('<' args+=(VID|TID) (',' args+=(VID|TID))* '>')? body=tableWrapper
    ;

//
// Tables & Elements:
//


tableElement
    : lhs_id=VID '::' ts=typeSpec        #typeValIdElement
    | lhs_id=VID '=' init_exp=expr       #bindValIdElement
    | lhs_id=TID '=' init_ts=typeSpec    #bindTypeIdElement
    | eval_exp=expr                      #forceEvalChainElement
    ;
tableWrapper
    : '{' (elements+=tableElement ';')* '}'
    ;
chainTableWrapper
    : '{' (elements+=tableElement ';')* (tail=expr)? '}'
    ;


//
// Module address prefixes:
//

moduleAddressPrefix
    :                                mod_name=VID ('<' args+=actualTemplateArg (',' args+=actualTemplateArg)* '>')? ':'
    | opt_prefix=moduleAddressPrefix mod_name=VID ('<' args+=actualTemplateArg (',' args+=actualTemplateArg)* '>')? ':'
    ;
actualTemplateArg
    : e=expr
    | t=typeSpec
    ;

//
// Expressions:
//

expr: bulkyExp
    ;

parenWrappedExp
    : '(' ')'                #unitExp
    | '(' wrapped=expr ')'   #identityParenExp
    | it=tuplePrimaryExp     #tupleExp
    ;
wrappedExp
    : it=parenWrappedExp    #throughWrappedExp
    | it=chainPrimaryExp    #chainExp
    | it=castPrimaryExp     #castExp
    ;
tuplePrimaryExp
    : '(' items+=expr (',' items+=expr)* ')'
    ;
chainPrimaryExp
    : (es=effectsSpec)? (ts=primaryTypeSpec)? chain_table_wrapper=chainTableWrapper
    ;
castPrimaryExp
    : ts=primaryTypeSpec data=parenWrappedExp
    ;

primaryExp
    : tk=VID                                #idExp
    | prefix=moduleAddressPrefix suffix=VID #idExpInModule
    | through=intPrimaryExp                 #throughIntPrimaryExp
    | tk=DEC_FLOAT                          #decFloatExp
    | it=stringPrimaryExp                   #stringExp
    | through=wrappedExp                    #throughParenPrimaryExp
    ;
intPrimaryExp
    : tk=DEC_INT    #decIntExp
    | tk=HEX_INT    #hexIntExp
    ;

stringPrimaryExp
    : (chunks+=stringChunk)+
    ;
stringChunk
    : tk=SQ_STRING      #sqStringChunk
    | tk=DQ_STRING      #dqStringChunk
    | tk=ML_DQ_STRING   #mlDqStringChunk
    | tk=ML_SQ_STRING   #mlSqStringChunk
    ;

postfixExp
    : through=primaryExp                                    #throughPostfixExp
    | called_exp=postfixExp (has_se='!')? arg=wrappedExp    #callExp
    | container_exp=postfixExp '[' ix=expr ']'              #getArrayElementExp
    | lhs=postfixExp '.' str_key=VID                        #dotNameKeyExp
    | lhs=postfixExp '.' int_key=intPrimaryExp              #dotIntKeyExp
    ;

unaryExp
    : through=postfixExp
    | op=unaryOp arg=unaryExp
    ;
unaryOp
    : 'not'
    | '+'
    | '-'
    ;

binaryExp
    : logicalOrBinaryExp
    ;
powBinaryExp
    : through=unaryExp
    | lt=powBinaryExp op='^' rt=unaryExp
    ;
mulBinaryExp
    : through=powBinaryExp
    | lt=mulBinaryExp op='*' rt=powBinaryExp
    | lt=mulBinaryExp op='/' rt=powBinaryExp
    | lt=mulBinaryExp op='%' rt=powBinaryExp
    ;
addBinaryExp
    : through=mulBinaryExp
    | lt=addBinaryExp op='+' rt=mulBinaryExp
    | lt=addBinaryExp op='-' rt=mulBinaryExp
    ;
cmpBinaryExp
    : through=addBinaryExp
    | lt=cmpBinaryExp op='<'  rt=addBinaryExp
    | lt=cmpBinaryExp op='>'  rt=addBinaryExp
    | lt=cmpBinaryExp op='<=' rt=addBinaryExp
    | lt=cmpBinaryExp op='>=' rt=addBinaryExp
    ;
eqBinaryExp
    : through=cmpBinaryExp
    | lt=eqBinaryExp op='==' rt=cmpBinaryExp
    | lt=eqBinaryExp op='!=' rt=cmpBinaryExp
    ;
logicalAndBinaryExp
    : through=eqBinaryExp
    | lt=logicalAndBinaryExp op='&' rt=eqBinaryExp
    ;
logicalOrBinaryExp
    : through=logicalAndBinaryExp
    | lt=logicalOrBinaryExp op='|' rt=logicalAndBinaryExp
    ;

assignExp
    : through=binaryExp
    | dst=assignExp ':=' src=binaryExp
    ;

bulkyExp
    : through=assignExp
    | if_exp=ifExp
    | fn_exp=fnExp
    | allocate_exp=allocateExp
    ;
ifExp
    : 'if' cond=wrappedExp then_branch=chainPrimaryExp ('else' opt_else_branch=elseBranchExp)?
    ;
elseBranchExp
    : chain_exp=chainPrimaryExp
    | if_exp=ifExp
    ;
fnExp
    : '(' (args+=VID ',')* (args+=VID)? ')' '->' body=expr
    ;
allocateExp
    : hint=allocatorHint (initializer=parenWrappedExp)
    | hint=allocatorHint '[' collection_ts=typeSpec '^' (size=expr|'?') ']' (initializer=parenWrappedExp)?
    ;
allocatorHint: 'make' | 'push' ;

//
// Type specs:
//

typeSpec
    : through=binaryTypeSpec
    ;
parenTypeSpec
    : '(' ')'                                               #unitTypeSpec
    | '(' wrapped=typeSpec ')'                              #identityParenTypeSpec
    | '(' (items+=typeSpec ',')+ (items+=typeSpec)? ')'     #tupleTypeSpec
    ;
primaryTypeSpec
    : tk=TID                                    #idTypeSpec
    | prefix=moduleAddressPrefix suffix=TID     #idTypeSpecInModule
    | through=parenTypeSpec                     #throughParenTypeSpec
    ;
unaryTypeSpec
    : through=primaryTypeSpec                           #throughUnaryTypeSpec
    | 'Struct' elements=tableWrapper                    #structTypeSpec
    | 'Enum' elements=tableWrapper                      #taggedUnionTypeSpec
    | 'Union' elements=tableWrapper                     #untaggedUnionTypeSpec
    | (is_mut='mut')? '[' t=typeSpec ',' n=expr ']'     #arrayTypeSpec
    | (is_mut='mut')? '[' t=typeSpec ',' '?' ']'        #sliceTypeSpec
    | (is_mut='mut')? '[' t=typeSpec ']'                #ptrTypeSpec
    ;
binaryTypeSpec
    : through=unaryTypeSpec                         #throughBinaryTypeSpec
    | lt=parenTypeSpec '->' rt=binaryTypeSpec       #fnSgnTypeSpec
    ;

//
// Effects specifiers:
//

effectsSpec
    : kw=('Tot'|'Dv'|'ST'|'Exn'|'ML')
    ;

//
// Tokens:
//

// IMPORTANT: CID before TID
TID : ('_'*) (U)   (L|U|D|'_')* ;
VID : ('_'*) (L)   (L|U|D|'_')*
    | ('_'*) ('_') (L|D|'_')*;

DEC_INT:             D (D|'_')* INT_SUFFIX?;
HEX_INT: ('0x'|'0X') H (H|'_')* INT_SUFFIX?;

DEC_FLOAT: DEC_INT '.' DEC_INT;

SQ_STRING: ('\'' (ANY_ESC|'\\\''|~[\r\n\\'])*?  '\'');
DQ_STRING: ('"'  (ANY_ESC|'\\"' |~[\r\n\\"])*?  '"');
ML_DQ_STRING: '"""' (.)*? '"""';
ML_SQ_STRING: '\'\'\'' (.)*? '\'\'\'';

fragment L: [a-z] ;
fragment U: [A-Z] ;
fragment D: [0-9] ;
fragment H: [0-9a-fA-F] ;
fragment INT_SUFFIX: (FLOAT_SUFFIX|[bBhHiIlLqQnN]) ;
fragment FLOAT_SUFFIX: [efd] ;

fragment ANY_ESC: (
    ('\\' ('\\' | 'n' | 'r' | 't')) |
    ('\\u' H H H H)
    ('\\U' H H H H H H H H)
);

//
// Ignore:
//

WS: (' '|'\t'|'\n') -> skip;

LINE_COMMENT: ('#' ~('\n')*) -> skip;
