# Author's Notes

_A manually updated blog about the documentation._ 

## 001 - Spec vs Tutorial

Jun 3

Created...
- `Tutorial`: first introduction to Qy
- `CompilerSpec`: technical specification of Qy and Qc. 


DOs:
- Be terse: using expert-targeted language
- Be precise and comprehensive: 
    - Talk about cases exhaustively and rigorously
    - Prefer directness to metaphors. Prefer repetition to compound sentences.
- Guide implementation:
    - include details relevant to a compiler implementation.
- Explain the toolchain
    - should be unambiguous what output/sizes produced regardless of platform (unlike C)

DONTs:
- justify using philosophy or design:
    - save it for the textbook, which may use such devices to help convey an abstraction of the data transforms at play
    - these tangents hide problems by introducing assumptions that may create new, false problems.
