# -*- coding: utf-8 -*-
import os
import sys

path = os.path.dirname(__file__)
sys.path.insert(0, path)

import Nodz

from setuptools import setup, find_packages

version = "1.3.0"


classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Utilities"
]


setup(
    name="Nodz",
    version=version,
    description="Python 2 compatible library to create nodes based graphs with Qt- "
                "It can work with any of PySide, PySide2, PyQt4 and PyQt5 thanks to the Qt.py module.",
    author="Loic LeGoff",
    author_email="loic.legoff9@gmail.com",
    url="https://github.com/LeGoffLoic/Nodz",
    license="MIT",
    zip_safe=False,
    package_data={'Nodz': ['default_config.json', 'pixmap.png']},
    packages=find_packages(),
    include_package_data=True,
    classifiers=classifiers
)