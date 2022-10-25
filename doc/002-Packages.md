A project is a directory with a `qy-project.json5` file in the root directory.

The project name is the same as the name of the folder containing this file.

The `qy-project.json5` file provides...
1.  metadata about the project
    - e.g. version
    - e.g. author
    - e.g. a description of the package's function
    - e.g. (optional) a homepage where the user can source this package
2.  dependencies
    - can source from Git, similar to `FetchContent` in CMake OR using the local 
      filesystem
    - optional version constraint, default to latest

A project may contain the following directories
1.  `source`: the root of Qy module files, automatically discovered (cf Rust).
    Can intersperse other file types in between, we only look at files with a
    `*.qy` extension, also recognizing sub-packages containing an `__init__.qy`
    file.
2.  `assets`: all files in this directory are copied into the same directory
    as the output executable. E.g. PIC object files, dependency executables, 
    3D models and textures, etc.
