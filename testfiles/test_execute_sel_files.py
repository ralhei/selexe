"""
UT functions to test loading and execution of pure selenese files
"""
import os
import sys
import subprocess

from selenium.common.exceptions import NoSuchElementException

sys.path.insert(0, '..')
from selexe import SelexeRunner

SELEXE_OPTIONS = {
    'driver': 'phantomjs',
    'executable_path': os.environ.get('PHANTOMJS_PATH', 'phantomjs'),
}

def setup_module():
    global testserver
    testserver = subprocess.Popen(['python', 'testserver.py'], cwd='../testserver',
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err = []
    '''for i in range(3):  # read max. 3 lines from stderr
        s = testserver.stderr.readline()
        err.append(s)
        if s.startswith('Listening on http'):
            # loop until the server is up and running
            break
    else:
        testserver.terminate()
        sys.stderr.write('\nError: Testserver (bottle.py) is not starting up properly! Messages:\n\n')
        for i in err:
            sys.stderr.write(i)
        sys.exit(1)'''


def teardown_module():
    testserver.terminate()


def test_simple_page():
    """run simple selenese test, without fixtures"""
    selexe = SelexeRunner('verifyTests.sel', **SELEXE_OPTIONS)
    res = selexe.run()
    assert res == []


def test_simple_form():
    """run simple selenese test, without fixtures"""
    selexe = SelexeRunner('form1.sel', **SELEXE_OPTIONS)
    res = selexe.run()
    assert res == []


def test_fixtures():
    """run empty selenese test file, just to check whether fixtures work"""
    selexe = SelexeRunner('fixtures.sel', fixtures='selexeFixtures.py', **SELEXE_OPTIONS)
    res = selexe.run()
    assert res == []
    

def test_fixtures_fail():
    """run empty selenese test file, just to check whether fixtures work
    Since fixtures argument is not given to SelexeRunner this test should fail.
    """
    selexe = SelexeRunner('fixtures.sel', fixtures=None, **SELEXE_OPTIONS)
    try:
        res = selexe.run()
    except NoSuchElementException:
        pass


def test_failing_test():
    """run simple selenese test, with verifyText find wrong string"""
    selexe = SelexeRunner('verifyTestFailing.sel', **SELEXE_OPTIONS)
    res = selexe.run()
    assert res == ['Actual value "DIV 1" did not match "This should fail!"']


