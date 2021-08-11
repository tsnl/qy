import os.path

from setuptools import setup, Extension
from Cython.Build import cythonize


def get_extension_lib_path():
    possible_shared_lib_name_list = [
        "./libExtensionLib.dylib",
    ]

    for possible_shared_lib_name in possible_shared_lib_name_list:
        if os.path.isfile(possible_shared_lib_name):
            return possible_shared_lib_name

    raise RuntimeError("Shared 'extension' lib not found: is it built?")


extension_lib_path = get_extension_lib_path()


def qy_cpp_extension(name, pyx_wrapper_file):
    return Extension(
        name,
        sources=[
            pyx_wrapper_file
        ],
        libraries=[
            extension_lib_path
        ],
        extra_compile_args=['-std=c++17'],
        language='c++'
    )


def main():
    setup(
        ext_modules=cythonize(
            module_list=[
                qy_cpp_extension("nexus", "nexus.pyx")
            ],
            compiler_directives={
                'language_level': '3'
            }
        ),
        requires=['setuptools',
                  'Cython']
    )


if __name__ == "__main__":
    main()
