import sys
from codecs import open
from os import path

import pybind11
from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext


HERE = path.abspath(path.dirname(__file__))


with open(path.join(HERE, "..", "..", "README.md"), encoding="utf-8") as f:
    long_description = f.read()


extras_require = {
    "docs": [
        "sphinx",
        "setuptools",
        "recommonmark",
        "sphinx_rtd_theme",
    ],
    "dev": [
        "setuptools",
        "pybind11>=2.6.0",
    ],
    "test-long-patches": [
        "deepdiff",
    ],
}


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""

    def build_extensions(self) -> None:
        ct = self.compiler.compiler_type

        # Compiler-specific options
        if ct == "msvc":
            for ext in self.extensions:
                ext.extra_compile_args = ["/std:c++17", "/O2", "/EHsc"]
        elif ct == "unix":
            for ext in self.extensions:
                ext.extra_compile_args = ["-std=c++17", "-O3", "-march=native"]
                if sys.platform == "darwin":
                    ext.extra_compile_args += [
                        "-stdlib=libc++",
                        "-mmacosx-version-min=10.14",
                    ]

        build_ext.build_extensions(self)


ext_modules = [
    Extension(
        "conflict_interface.replay.steiner_tree_cpp",
        sources=[
            path.join("conflict_interface", "replay", "steiner_tree.cpp"),
        ],
        include_dirs=[pybind11.get_include()],
        language="c++",
    ),
    Extension(
        "conflict_interface.replay.op_tree_cpp",
        sources=[
            path.join("conflict_interface", "replay", "op_tree.cpp"),
        ],
        include_dirs=[pybind11.get_include()],
        language="c++",
    ),
]


setup(
    name="conflict-interface",
    version="0.1.2",
    description="Conflict of Nations Interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://conflict-interface.readthedocs.io/",
    author="zDox",
    author_email="",
    license="Proprietary",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(where=".", include=["conflict_interface*"]),
    include_package_data=True,
    install_requires=[
        "setuptools",
        "requests",
        "requests[socks]",
        "fake_useragent",
        "lxml",
        "numpy",
        "shapely",
        "cloudscraper25",
        "msgpack",
        "zstandard",
        "lz4",
        "msgspec",
        "scipy",
        "orjson",
        "pybind11>=2.6.0",
    ],
    extras_require=extras_require,
    ext_modules=ext_modules,
    cmdclass={"build_ext": BuildExt},
    zip_safe=False,
)