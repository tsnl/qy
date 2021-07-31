from setuptools import setup, Extension
from Cython.Build import cythonize


def main():
    setup(
        ext_modules=cythonize(
            module_list=[
                Extension(
                    "mast",
                    ["./mast.pyx"]
                )
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
