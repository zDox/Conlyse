from setuptools import find_packages
from setuptools import setup
# To use a consistent encoding
from codecs import open
from os import path

# The directory containing this file
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# This call to setup() does all the work
# noinspection PyPackageRequirements
setup(
    name="conflict-interface",
    version="0.1.0",
    description="Conflict of Nations Interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://conflict-interface.readthedocs.io/",
    author="zDox",
    author_email="",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent"
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=["requests", "requests[socks]", "fake_useragent", "lxml", "numpy", "shapely", "jsonpatch"],
    extras_require =
    {
        "docs": [
            "sphinx",
            "setuptools",
            "recommonmark",
            "sphinx_rtd_theme",
        ],
        "dev": [
            "setuptools",
        ]
    },
)
