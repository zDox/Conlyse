import sys
from codecs import open
from os import path

import pybind11
from setuptools import Extension
from setuptools import find_packages
from setuptools import setup
from setuptools.command.build_ext import build_ext

# The directory containing this file
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Define base extras first
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
    "tools-replay-debug": [
        "python-dateutil",
    ],
    "tools-recording-converter": [
        "tqdm"
    ],
    "tools-recorder": [
        # Add dependencies for recorder tool here
    ],
    "tools-server-observer": [
        "httpx",
        "httpx[socks]"
    ],
    "test-long-patches": [
        "deepdiff"
    ]
}

# Create a meta-extra that installs all tools dynamically
tools_extras = [
    dep
    for key, deps in extras_require.items()
    if key.startswith("tools-")
    for dep in deps
]

test_extras = [
    dep
    for key, deps in extras_require.items()
    if key.startswith("test-")
    for dep in deps
]

extras_require["tests"] = tools_extras + test_extras


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""

    def build_extensions(self):
        ct = self.compiler.compiler_type

        # Compiler-specific options
        if ct == 'msvc':
            for ext in self.extensions:
                ext.extra_compile_args = ['/std:c++17', '/O2', '/EHsc']
        elif ct == 'unix':
            for ext in self.extensions:
                ext.extra_compile_args = ['-std=c++17', '-O3', '-march=native']
                if sys.platform == 'darwin':
                    ext.extra_compile_args += ['-stdlib=libc++', '-mmacosx-version-min=10.14']

        build_ext.build_extensions(self)


ext_modules = [
    Extension(
        'conflict_interface.replay.steiner_tree_cpp',
        sources=['conflict_interface/replay/steiner_tree.cpp'],
        include_dirs=[pybind11.get_include()],
        language='c++',
    ),
    Extension(
        'conflict_interface.replay.op_tree_cpp',
        sources=['conflict_interface/replay/op_tree.cpp'],
        include_dirs=[pybind11.get_include()],
        language='c++',
    ),
]

# This call to setup() does all the work
setup(
    name="conflict-interface",
    version="0.1.2",
    description="Conflict of Nations Interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://conflict-interface.readthedocs.io/",
    author="zDox",
    author_email="",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent"
    ],
    packages=find_packages(),
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
    cmdclass={'build_ext': BuildExt},
    entry_points={
        "console_scripts": [
            "recorder=tools.recorder.__main__:main",
            "replay-debug=tools.replay_debug.__main__:main",
            "recording-converter=tools.recording_converter.__main__:main",
            # server-observer is now a C++ binary, build from tools/server_observer_cpp/
        ],
    },
    zip_safe=False,
)