
try:
    from selexe_runner import SelexeRunner, SelexeError
except ImportError:
    import os
    if not 'RAN_BY_SETUP_PY' in os.environ:
        raise

import warnings
warnings.filterwarnings('once', category=DeprecationWarning) # show all deprecated warning only once
del warnings

__version__ = '0.2.0'