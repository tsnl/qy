"""
This module is a bag of checks that can be completed after successfully typing.
1. Ensure each symbol is bound to only once per context.
    - this may not be required for local vars!
      WIP in the `inference` submodule of typer to elide this requirement.
2. Ensure mutability for memory windows are correct.
3. Ensure SES are correct for functions.
4. Ensure initialization orders are valid for all symbols.
"""