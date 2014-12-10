
try:
    from selexe_runner import SelexeRunner, SelexeError
except ImportError:
    import os
    if not os.environ.get('RAN_BY_SETUP_PY', False):
        raise

import warnings
warnings.filterwarnings('once', category=DeprecationWarning) # show all deprecated warning only once
del warnings

__version__ = '0.2.0'