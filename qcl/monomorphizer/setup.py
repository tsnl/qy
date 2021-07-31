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
        ),
        requires=['setuptools',
                  'Cython']
    )


if __name__ == "__main__":
    main()
