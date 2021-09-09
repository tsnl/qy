#!/usr/bin/env python3.9

import sys
import os.path

from setuptools import setup, Extension
from Cython.Build import cythonize


if sys.platform.startswith('win32'):
    extra_compile_args = ['/std:c++17']
    # TODO: replace with 'Release/CppMonomorphizerExt.lib' with a flag.
    library_list = ["Release/CppMonomorphizerExt"]
    library_dir_list = ["Debug/"]
else:
    extra_compile_args = ["-std=c++17"]
    library_list = ["libCppMonomorphizerExt.a"]
    library_dir_list = []


def mk_wrapper_extension():
    return Extension(
        "wrapper",
        sources=["wrapper.pyx"],
        libraries=library_list,
        library_dir_list=library_dir_list,
        extra_compile_args=extra_compile_args,
        language='c++'
    )


def mk_copier_extension():
    return Extension(
        "copier",
        sources=["copier.pyx"],
        extra_compile_args=extra_compile_args,
        language='c++'
    )


def main():
    setup(
        ext_modules=cythonize(
            module_list=[
                mk_wrapper_extension(),
                mk_copier_extension()
            ],
            compiler_directives={
                'language_level': '3'
            }
        ),
        requires=[
            'setuptools',
            'Cython'
        ],
        include_dirs=["."]
    )


if __name__ == "__main__":
    main()
