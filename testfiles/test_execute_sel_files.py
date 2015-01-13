"""
UT functions to test loading and execution of pure selenese files
"""
import os
import sys
import subprocess

from selenium.common.exceptions import NoSuchElementException

from environment import SELEXE_DRIVER, SELEXE_TIMEOUT, SELEXE_BASEURI, PHANTOMJS_PATH, SELEXE_TESTSERVER_PORT
sys.path.insert(0, '..')
from selexe import SelexeRunner

SELEXE_OPTIONS = {
    'driver': SELEXE_DRIVER,
    'timeout': SELEXE_TIMEOUT,
    'baseuri': SELEXE_BASEURI,
}
if SELEXE_DRIVER == 'phantomjs':
    SELEXE_OPTIONS['executable_path'] = PHANTOMJS_PATH

def setup_module():
    setup_module.testserver = subprocess.Popen(('python', 'testserver.py', '%d' % SELEXE_TESTSERVER_PORT), cwd='../testserver')


def teardown_module():
    setup_module.testserver.terminate()


def test_simple_page():
    """run simple selenese test, without fixtures"""
    selexe = SelexeRunner('verifyTests.sel', **SELEXE_OPTIONS)
    errors = selexe.run()
    assert not errors


def test_simple_form():
    """run simple selenese test, without fixtures"""
    selexe = SelexeRunner('form1.sel', **SELEXE_OPTIONS)
    errors = selexe.run()
    assert not errors


def test_fixtures():
    """run empty selenese test file, just to check whether fixtures work"""
    selexe = SelexeRunner('fixtures.sel', fixtures='selexeFixtures.py', **SELEXE_OPTIONS)
    errors = selexe.run()
    assert not errors
    

def test_fixtures_fail():
    """run empty selenese test file, just to check whether fixtures work
    Since fixtures argument is not given to SelexeRunner this test should fail.
    """
    selexe = SelexeRunner('fixtures.sel', fixtures=None, **SELEXE_OPTIONS)
    try:
        errors = selexe.run()
    except NoSuchElementException:
        pass


def test_failing_test():
    """run simple selenese test, with verifyText find wrong string"""
    selexe = SelexeRunner('verifyTestFailing.sel', **SELEXE_OPTIONS)
    errors = selexe.run()
    assert errors
