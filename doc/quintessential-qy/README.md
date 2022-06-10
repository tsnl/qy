# Quintessential Qy

This is an e-book designed to introduce programmers to the Qy programming language.
It does not presume familiarity with any existing programming languages.
However, it does presume familiarity with the command-line and general computer
proficiency.

Qy is a systems programming language whose goal is to provide an extremely 
low-level environment, comparable to C or assembly, along with a compiler that 
allows users to build more complex features from within the language.
One example of this approach is the QEMU object system, which allows users to define
classes, interfaces, and relationships between them using C macros and values.
Another example of this approach is the Scheme programming language, where macros
atop a very simple set of rules can produce a rich and extensible environment.
By giving the programmer general tools with which to build new language features,
Qy demystifies compilation while enabling a broad range of programming disciplines,
all of which have historically 'targeted' (at run-time or compile-time) very similar
CPU ISAs that both C and Qy thinly abstract.

If this you are not a fan of reading, some other useful resources within the codebase 
include...
-   the grammar, which declaratively specifies how all of Qy's syntax works <br/>
    [/grammars/QySourceFile.g4](../../grammars/QySourceFile.g4)
-   examples in the `eg` folder, all of which are maintained and kept simple. <br/>
    [/eg](../../eg/README.md)

Finally, if you notice any errors or would like to contribute, please either...
-   yell at me over email via [nikhilidiculla@gmail.com](mailto:nikhilidiculla@gmail.com)
-   submit a pull-request with a correction

## Table of Contents

<TODO>