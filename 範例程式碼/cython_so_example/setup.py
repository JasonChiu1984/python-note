from setuptools import Extension, setup
from Cython.Build import cythonize


extensions = [
    Extension("fastmath._core", ["src/fastmath/_core.pyx"]),
]


setup(
    packages=["fastmath"],
    package_dir={"": "src"},
    ext_modules=cythonize(extensions, language_level=3),
)
