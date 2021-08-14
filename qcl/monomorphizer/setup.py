#!/usr/bin/env python3.9

import os.path

from setuptools import setup, Extension
from Cython.Build import cythonize


def mk_wrapper_extension():
    return Extension(
        "wrapper",
        sources=[
            "wrapper.pyx",
            # "extension/arg-list.cc",
            # "extension/gdef.cc",
            # "extension/eval.cc",
            # "extension/mast.cc",
            # "extension/modules.cc",
            # "extension/mtype.cc",
            # "extension/mval.cc",
            # "extension/sub.cc"
        ],
        extra_objects=[
            "libCppMonomorphizerExt.a"
        ],
        extra_compile_args=[
            "-std=c++17",
        ],
        language='c++'
    )


def mk_copier_extension():
    return Extension(
        "copier",
        sources=[
            "copier.pyx"
        ],
        extra_compile_args=[
            '-std=c++17'
        ],
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
