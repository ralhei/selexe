import os
import warnings
from pkg_resources import parse_version

from .selexe_runner import SelexeRunner, SelexeError
from .__main__ import SelexeArgumentParser

warnings.filterwarnings('once', category=DeprecationWarning)  # show all deprecated warning only once
del warnings

__version_str__ = open(os.path.join(os.path.dirname(__file__), 'version.txt')).readline().strip()
__version__ = parse_version(__version_str__)
