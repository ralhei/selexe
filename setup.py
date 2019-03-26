#!/usr/bin/env python

import os
from setuptools import setup

# Get long_description from intro.txt:
here = os.path.dirname(os.path.abspath(__file__))
f = open(os.path.join(here, 'doc', 'intro.rst'))
long_description = f.read()
f.close()

requirements = open('requirements.txt').read().splitlines()
version = open('selexe/version.txt').readline()[:-1]

setup(name='selexe',
      version=version,
      description='A tool to directly execute selenese files created by Selenium IDE',
      long_description=long_description,
      author='Ralph Heinkel',
      author_email='rh [at] ralph-heinkel.com',
      url='http://pypi.python.org/pypi/selexe/',
      packages=['selexe', 'selexe.contrib'],
      install_requires=requirements,
      entry_points={
          'console_scripts': ['selexe=selexe.__main__:main'],
      },
      license='MIT license',
      platforms=['unix', 'linux', 'cygwin', 'win32'],
      zip_save=False,
      classifiers=['Development Status :: 3 - Alpha',
                   'Environment :: Console',
                   'License :: OSI Approved :: MIT License',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 3.6',
                   'Programming Language :: Python :: 3.7',
                   'Operating System :: POSIX',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: MacOS :: MacOS X',
                   'Programming Language :: Python',
                   'Intended Audience :: Developers',
                   'Topic :: Software Development :: Testing',
                   ],
      )
