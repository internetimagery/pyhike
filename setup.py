#!/usr/bin/env python

import re
import sys
import os.path
from distutils.core import setup


root = os.path.dirname(__file__)
# with open(os.path.join(root, "README.md")) as handle:
#     readme = handle.read()

with open(os.path.join(root, "pyhike", "__init__.py")) as handle:
    version = re.search(r"__version__ *= *['\"]([^'\"]*)['\"]", handle.read()).group(1)

setup(
    name="pyhike",
    version=version,
    description="Have an adventure traveling through code!",
    long_description="See https://github.com/internetimagery/pyhike",
    #    long_description=readme,
    #    long_description_content_type="text/markdown",
    long_description_content_type="text/plain",
    author="Jason Dixon",
    url="https://github.com/internetimagery/pyhike",
    keywords=["development", "traversal"],
    packages=["pyhike"],
    install_requires=[],
    extras_require={':python_version in "2.7 3.2 3.3 3.4"': ["typing>=0.4"]},
    # install_requires=["funcsigs"] if sys.version_info[0] == 2 else [],
    # python_requires=">=2.7,>=3.6",
    python_requires=">=2.7",
    license="MIT",
)
