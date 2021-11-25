## P5: Next Steps

(`git checkout` the commit when this README was added)

1.  PROPOSAL: Fork this branch. Qc-v2.1 one will eventually become an archive branch.
    -   Qc-v2.1 is pretty much just C.
    -   Right now, the compiler works fine on most native code, but is lacking a few key features.
    -   Right now, the language has 0 lines of code in 'ecosystem' features. Must use C++'s ecosystem.
    
    -  Before forking, take the time to audit, write tests, and refactor. 
        -   TODO: clean up any stubs in the existing code-base
            -   e.g. (at time of writing) emitting Constructor expressions (because we need to emit constructors)
        -   TODO: add namespaces
            -   should be able to use TIDs (including ones bound to types) as namespaces
                -   e.g. invoking methods in classes imported from C++
            -   should group symbols into a namespace
        -   TODO: allow the user to add C++ libraries
            -   should be able to import C++ source code, most notably `cstdio`
            -   should be able to instantiate C++ constructs
            -   should NOT be able to invoke methods except...
                -   static ones via class-based method-call syntax.
                -   constructors and destructors implicitly (treated like 'builtin magic' for now)
            -   should NOT be able to define classes, derive from C++ classes, etc.
        -   TODO: add builtin support for **reflection**
            -   investigate C++'s run-time type info system (since we need to interop with C++ anyway)
            -   can fill in C++ RTTI using libclang, but means we link with C++ with source-only.

    -   Propose **qc-v2.1 the fork test**: does this branch...
        -   produce correct C++ output given valid input?
        -   detect all cases of invalid input correctly?
        -   crash/indefinitely loop/produce inadequate error messages?

2.  Tentative road-map:
    -   `qc-v2`
        -   `qc-v2.2`: add support for interfaces, 'impl' statements, operator overloads, ctor/dtor, assignment, ...
        -   `qc-v2.3`: templates & iterative compilation aka compile-time execution
        -   `qc-v2.4`: macros! 
        -   `qc-v2.5`: improved feedback + code cleanup and optimization.
            -   No new functionality; just make the tool nicer to use.
            -   MAYBE includes LSP server support
            
        -   Beyond this point, time is better spent implementing functionality in features.
            -   MAYBE `qc-v2.5.1`, ... such that `qc-v2.5.*` is an LTS line
        
        -   Can implement library features like...
            -   Builtin `python3` interpreter support:
                -   overcome one of Python's key limitations, inability to multi-thread, by running your own 
                    sub-processes
                -   support for interfacing with NumPy arrays along with other Python datatypes
                -   allow Qy users to write Python code using 'monotype' system (e.g. `py::len`)
                -   tap into an incredibly rich package ecosystem
            -   Macro-based serialization

    -   `qc-v3`
            Possible features in the future could include:
            -   self-hosting (which should bring a good performance improvement)
            -   supporting more platforms/backends, simplifying the build process and allowing for interpreters
                -   e.g. lowered backends like LLVM IR and C
                -   e.g. optimizations for specific standard library features like Python execution
