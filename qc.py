# TODO: write a compiler. :)

"""
NOTE: can use the typer of Astropod, with some modifications to correctly type modules and submodules (imports).
NOTE: rather than an AST, use ANTLR + visitors-- more than 3 post-passes should not be required: type, Z3, emit.
NOTE: use a single file to implement this compiler.
    - not large enough that it requires multiple files (at this point)
        - dependencies do all the heavy lifting
    - ultimate portability: easy to add this repository as a submodule in any project to use as a toolchain
"""


