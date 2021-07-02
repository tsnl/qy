from setuptools import setup, Extension
from Cython.Build import cythonize


def main():
    setup(
        ext_modules=cythonize(
            module_list=[
                Extension(
                    "pyvm",
                    ["./pyvm.pyx",
                     "./impl/vm.c",
                     "./impl/table.c",
                     "./impl/expr.c",
                     "./impl/rtti.c"]
                )
            ],
        ),
        requires=['setuptools',
                  'Cython']
    )


if __name__ == "__main__":
    main()
