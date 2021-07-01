from setuptools import setup, Extension
from Cython.Build import cythonize


def main():
    setup(
        ext_modules=cythonize(
            module_list=[
                Extension(
                    "vm",
                    ["./vm.pyx",
                     "vm-impl/value.cc",
                     "vm-impl/exp.cc",
                     "vm-impl/func.cc",
                     "vm-impl/vm.impl.cc",
                     "vm-impl/vm.interface.cc"]
                )
            ],
        ),
        requires=['setuptools', 'Cython']
    )


if __name__ == "__main__":
    main()
