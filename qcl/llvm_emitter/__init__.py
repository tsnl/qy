from . import emitter


def run():
    print(">- BEG of LLVM emitter -<")

    # FIXME: need some way to get substitution used to instantiate PolyMod into MonoMod
    #   - can obtain this from ArgList, translating mtype.TID to types.TID
    #   - can then generate a substitution and an AST node reference (for LambdaExp)
    #   - applying sub to existing types yields subbed types, true for any types in MonoModID

    # TODO: implement this PLAN:
    #   - first, declare all synthetic functions (one per lambda) and global variables
    #       - requires info about implicit arguments
    #   - next, process function definitions & global variable initializers

    e = emitter.Emitter()
    e.emit_project("qy-build/output-1.ir")

    print(">- END of LLVM emitter -<")

