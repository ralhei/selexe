#!/usr/bin/env python

import os
from setuptools import setup

## Get long_description from intro.txt:
here = os.path.dirname(os.path.abspath(__file__))
f = open(os.path.join(here, 'doc', 'intro.rst'))
long_description = f.read()
f.close()

# Import avoiding inner import errors
os.environ['RAN_BY_SETUP_PY'] = 'true'
from selexe import __version__

setup(name='selexe',
      version=__version__,
      description='A tool to directly execute selenese files created by Selenium IDE',
      long_description=long_description,
      author='Ralph Heinkel',
      author_email='rh [at] ralph-heinkel.com',
      url='http://pypi.python.org/pypi/selexe/',
      packages=['selexe', 'selexe.contrib'],
      install_requires=['selenium', 'beautifulsoup4', 'six'],
      entry_points = { 'console_scripts': ['selexe=selexe.__main__:main'],
                       },
      license='MIT license',
      platforms=['unix', 'linux', 'cygwin', 'win32'],
      zip_save=False,
      classifiers=[ 'Development Status :: 3 - Alpha',
                    'Environment :: Console',
                    'License :: OSI Approved :: MIT License',
                    'Operating System :: POSIX',
                    'Operating System :: Microsoft :: Windows',
                    'Operating System :: MacOS :: MacOS X',
                    'Programming Language :: Python',
                    'Intended Audience :: Developers',
                    'Topic :: Software Development :: Testing',
                    ],
     )
