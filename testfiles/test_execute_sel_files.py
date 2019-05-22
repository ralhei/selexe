"""
UT functions to test loading and execution of pure selenese files
"""
import sys

from selenium.common.exceptions import NoSuchElementException
sys.path.insert(0, '..')
from selexe import SelexeRunner
from environment import SELEXE_DRIVER, SELEXE_BASEURI, PHANTOMJS_PATH, SELEXE_TESTSERVER_PORT  # noqa


SELEXE_OPTIONS = {
    'driver': SELEXE_DRIVER,
    'baseuri': SELEXE_BASEURI,
}
if SELEXE_DRIVER == 'phantomjs':
    SELEXE_OPTIONS['executable_path'] = PHANTOMJS_PATH


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
        selexe.run()
    except NoSuchElementException:
        pass


def test_failing_test():
    """run simple selenese test, with verifyText find wrong string"""
    selexe = SelexeRunner('verifyTestFailing.sel', **SELEXE_OPTIONS)
    errors = selexe.run()
    assert errors
