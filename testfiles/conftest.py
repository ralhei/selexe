import subprocess

import pytest

from environment import SELEXE_TESTSERVER_PORT  # noqa


@pytest.fixture(scope='module', autouse=True)
def testserver():
    testserver = subprocess.Popen(('python', 'testserver.py', '%d' % SELEXE_TESTSERVER_PORT), cwd='../testserver')
    try:
        yield  # yield to run the actual unittest function
    finally:
        testserver.terminate()
