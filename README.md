# `qy-v3`

A vastly simplified take on Qy.
1.  No templates, no compile-time evaluation: instead, dynamically typed and interpreted
2.  No explicit type system, language is trivially manifestly typed.
    - unlike Julia, which relies on JIT template expansion, or Crystal, which implicitly unifies, we do something else.
    - every function is a constructor of its own data-type.
    - we can perform control-flow analysis to infer and type-check the whole system without any annotations.
    - until this is feasible, can use a placeholder system that is not very efficient, but 'good enough' for testing and
      excellent for debugging
    - **unification errors** are typing errors, but we can add ways for the unifier to 'auto fix' (built-in only)
3.  Initially, assume functions are not first-class.
    - this helps us optimize one of the most important operations we execute
4.  Symbols denoted by back-quoted strings (?)
5.  Syntax need not be indentation sensitive
    - keyword-based languages typically have a terminator keyword (e.g. `end` in basic, `fi` in bash)
    - control-flow gives us certain keywords we expect to terminate blocks-- use these
        - only oddball: 'if': not an expression, just subdivides into more blocks
        - block terminators: `continue`, `break`, `return`, etc


```
; Semicolons begin line comments, and are not used as delimiters.
; Only top-level statements are 'def', 'use', and 'chk'

; NOTE: each file is a module, and is processed as one translation unit.
;       this lets the user define stuff out of order. ^_^

;
; 'USE' statement:
;

; 'use' is like import in Python, but from any file path.
use basic from "random-qy3-file-path.qy3"

;
; 'DEF' & 'VAL' statements:
;

; used to define functions, which are polymorphically typed by default.
; NOTE: top-level functions are also generic type definitions.
;       you can use a function name to identify the data-type it returns.

def point_v1 (xyz, r, c) =
    return {
        pos: xyz,
        r: r, 
        c: c
    }

def point_v2 (xyz, rc) = 
    return {
        pos: xyz,
        rc: rc
    }

def use_point_v1 = false

; discriminated unions expressed via named return branches
; **discriminated unions are always boxed.**
def point (x, y, z, r, c) =
    if use_point_v1 then
        return.Point1 point_v1()
    else
        return.Point2 point_v2()

; note 'is' operator is compile-time OR run-time (unions only)
def process_pts (pt_list) =
    for pt in pt_list do
        if pt is point.Point1 then
            # do point 1 specific stuff
        elif pt is point.Point2 then
            # do point 2 specific stuff
        else
            # 'panic' is checked for at compile-time-- 
            # if the compiler can prove a program may panic, it is taken as a compile-time error.
            panic "Unknown 'point' type"

        continue

; TODO: what about references? vectors?
; maybe can offer these as built-ins, with user-managed 'handles' and the option to index
; challenge is getting good handles-- maybe scheme locatives are what we need?
; alternatively, can offer 'vector' as a built-in, and let the user slice it as required (no references, just indices)

; TODO: what about interfaces, dynamic dispatch?
;   - can just use a procedural approach?
;   - pattern matching allows us to dynamic dispatch?
;     - so optional type annotations auto-pattern-match
;     - so overloads are a thing
;     - can use a Nim-style de-sugaring for `.method`

;
; EXAMPLES OF ERRORS
;

; unification error: 
; all function return branches must return a value with the same datatype or use named return 
; branches to box

; WRONG
def optional (is_some, v) =
    if is_some then
        return {`Some`, v}
    else
        return {`None`, void}

; RIGHT
def optional (is_some, v) =
    if is_some then
        return.Some v
    else
        return.None void
```


