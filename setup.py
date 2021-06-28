from setuptools import setup, Extension
from Cython.Build import cythonize


def main():
    setup(
        ext_modules=cythonize(
            module_list=[
                Extension(
                    "wrapper",
                    ["qcl/interpretation/wrapper.pyx",
                     "qcl/interpretation/vm.cc"]
                ),
            ],
            language='c++'
        ),
        requires=['setuptools', 'Cython']
    )


if __name__ == "__main__":
    main()
