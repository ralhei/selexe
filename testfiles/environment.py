import os

SELEXE_DRIVER = os.environ.get('SELEXE_DRIVER', 'phantomjs')
SELEXE_TIMEOUT = int(os.environ.get('SELEXE_TIMEOUT', '1000'), 10)
SELEXE_TESTSERVER_PORT = int(os.environ.get('SELEXE_TESTSERVER_PORT', '8080'), 10)
SELEXE_BASEURI = 'http://localhost:%d' % SELEXE_TESTSERVER_PORT
SELEXE_SKIP_ALERT = bool(os.environ.get('SELEXE_SKIP_ALERT', SELEXE_DRIVER=='phantomjs'))
PHANTOMJS_PATH = os.environ.get('PHANTOMJS_PATH', 'phantomjs')