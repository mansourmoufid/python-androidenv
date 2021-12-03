#!/usr/bin/env python

import androidenv


_classifiers = [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: ISC License (ISCL)',
    'Operating System :: Android',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Build Tools',
]

with open('README.md', 'r') as readme:
    _long_description = readme.read()


if __name__ == '__main__':

    try:
        from setuptools import setup
    except ImportError:
        from distutils.core import setup

    setup(
        author=androidenv.__author__,
        author_email=androidenv.__email__,
        classifiers=_classifiers,
        description=androidenv.__doc__,
        license=androidenv.__license__,
        long_description=_long_description,
        long_description_content_type='text/markdown',
        name='androidenv',
        py_modules=['androidenv'],
        url='https://github.com/eliteraspberries/python-androidenv',
        version=androidenv.__version__,
    )
