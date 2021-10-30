## module system

How modules work are key because...
- a good module system promotes code reuse and making libraries
- isolated modules allow compilation to be parallelized easily

Rather than 'include' or 'import', simply load all source code into a global namespace
- exploit the fact that linker consolidates symbols anyway, forcing uniqueness
- allow the user to invoke the compiler on a compiler-config file, provides a source list and compiler flags
  - each compiler-config file `*-cc.json`
- ~~symbols in global namespace automatically made available everywhere~~
- symbols in different modules must be explicitly `use`-d; akin to a hole, to be linked later.

Code is broken into **packages**, such that...
- each package is a **single directory** containing a file with `.qyp.json` extension
- by placing such a JSON in each directory, we can stitch together...
    - neighboring directories
    - remote repostiories

Compiler accepts a single `.qyp.json` file as an argument.
- can expand each package recursively into a graph
- can then compile each node in parallel

```
{
    "name": "sandbox",
    "author": "TSNL",
    "help": "This module contains several Qy examples being used as tests to develop the compiler.",
    "src": [
        "./source1.qy",
        "./source2.qy",
        "./source3.qy",
    ],
    "deps": [
        "./helper/helper.qyp.json",
        "https://github.com/tsnl/qy-stdlib-v1"
    ]
}
```
