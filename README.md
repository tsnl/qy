# `Q4` - Version 4 of the Qy Programming Language

(WIP)

Q4 is a systems programming language that feels like Python.

If we think of compilers as accepting scripts that program them to produce certain output, then this script is purely declarative for all existing programming languages.

Instead, Q4 uses an imperative scripting environment, and exploits the fact that iteratively JIT-ing each statement and linking into a larger accumulated object produces the desired compiled output within a closure.

Q4c compiles code in a single pass, loading and executing each statement iteratively just in time.
During this loading process, any statement may invoke any prior statement (at compile-time) to compute results to integrate into the next statement.
Combined with boxing and type inference, this produces a manifestly-typed language with a dynamic feel, since the user can evaluate and instantiate anything anywhere.

Message passing is a key feature of this language. It allows...
-   user-programmable manual memory management: define 'heap' objects as an interface to raw memory: implement your own collectors to work with a managed heap.
-   complex metatyping: since types are first-class objects, it should be possible to define complex data-types and perform/embed refinement checks 
    -   iterative compilation clearly communicates where the compiler will interpose on user flow (between statements)
    -   first-class types allow the user to specify messages that are invoked during type-checks at compile-time
    -   first-class everything allows the compiler to easily interface with the heap and read existing functions, values, etc.
-   elegant compile-time evaluation
    -   (Motivating backstory + comparison to C++ constexpr evaluation)
    
        In Qy-v1 (haha), I developed a sophisticated compile-time execution mechanism that allowed arbitrary expressions to be evaluated at compile time.

        I was dissatisfied with its abilities, because like C++, it could only evaluate `constexpr` statements, and for good reason: the heap is frozen during compile-time evaluation because the heap does not exist yet.

        However, such compile-time evaluation was required to specify inputs to templates, a key feature of metaprogramming.

        This meant that much of the language tended toward a functional style, devoid of side-effects.

        Unfortunately, this **prevented me from solving my real-world issues** related to pre-processing data files during compile-time: wouldn't it be best if
        we could parse data files into optimized blobs during compile-time?

        **This approach overcomes these issues in the following ways...** 
    
    -   templates are now powered by a full-fledged runtime, using imperative, stateful calculations.

    -   this permits **arbitrary compile-time evaluation and the creation of rich data-structures in a way that is simplest for the user.**

        In interpreted mode, a 'main' callback defined by the user is invoked immediately after compiling/evaluating each statement.
        After compiling/evaluating each statement, the source code is frozen, and no more computation can occur unless we invoke a function, so we can compile any loaded functions into an executable, confident that any future function calls will be within a closure ball covered by this executable.

        When the program is compiled to an executable, we 'freeze' the state immediately before calling 'main', saving it to an executable file.

        Thus, a programmer may treat any code evaluated during load-time as 'compile-time' evaluation, and any code invoked from a bound entry point as
        'run-time' evaluation.

See [doc/001.Manual.md](/doc/001.Manual.md) for notes about the language.

## Build Instructions

-   Requirements:
    -   (On Linux) install these packages (for Ubuntu): `pkg-config`, `uuid-dev`
    -   CMake + a CMake-compatible C++ build toolchain
    -   A recent Java runtime environment
-   Run `scripts/setup.001-antlr_build.*` based on your platform.
    -   Builds ANTLR
    -   Generates C++ source code from grammar
-   Build this project with CMake.
    
    (Make a build directory, configure with this repo's root as the source directory, configure and build using your CMake toolchain)

    ```bash
    $ pwd
    # should display the path to where you cloned this repo
    $ cd build
    # on Linux:
        $ ccmake ..
    # on Windows:
        $ cmake-gui ..
    # ...configure your build, then...
    $ cmake ..
    $ cmake --build .
    # may need to run `cmake --build .` twice if clock skew is detected (e.g. on WSL)
    $ cd ..
    ```

Then, run the `q4c` executable with no arguments to see help.
-   Run `$ q4c <target-file-path>` to interpret a specified file
-   Run `$ q4c <target-file-path> -o <output-file-path>` to compile an output executable, then exit. Use `-x` instead of `-o` to execute after
building.
-   Run `$ q4c` or `$ q4c -h` to print help.


## Resources

-   https://llvm.org/docs/tutorial/BuildingAJIT1.html

    "just referencing a definition, even if it is never used, will be enough to trigger compilation": just what we want [for now, at least?].

-   See: https://tomassetti.me/getting-started-antlr-cpp/
