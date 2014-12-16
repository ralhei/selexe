#!/usr/bin/env python

import sys
import os
import os.path
import logging
import pdb
import functools
import time
import timeit

from selenium import webdriver
from parse_sel import SeleniumParser
from selenium_driver import SeleniumDriver
from cmdargs import DEFAULT_FIXTURES_FILE


logger = logging.getLogger(__name__)


class SelexeError(Exception):
    """Custom Selexe error class"""
    pass


class SelexeRunner(object):
    """
    Selenium file execution class
    """
    parser_class = SeleniumParser
    driver_class = SeleniumDriver
    webdriver_classes = {
        'firefox': webdriver.Firefox,
        'chrome': webdriver.Chrome,
        'ie': webdriver.Ie,
        'opera': webdriver.Opera,
        'safari': webdriver.Safari,
        'phantomjs': webdriver.PhantomJS,
        'android': webdriver.Android,
        'remote': webdriver.Remote,
    }
    webdriver_timeout_support = ('firefox', 'ie')

    def __init__(self, filename, baseuri=None, fixtures=None, pmd=False, timeit=False, driver='firefox',
                 window_size=None, encoding='utf-8', timeout=10000, error_screenshot_dir=None, **options):
        """
        @param filename: Selenium IDE file
        @param baseuri: base url for selenium tests
        @param fixtures:
        @param pmd: launches pdb on fail if True, defaults to False
        @param timeit: logs time taken by every command on logging level INFO if True, defaults to False
        @param driver: selenium driver as string, defaults to 'firefox'
        @param window_size: desired window size as (width, height) tuple, defaults to None
        @param encoding: encoding will be used by Selenium IDE test parser
        @param timeout: maximum milliseconds will be waited for every command before failing, defaults to 10000 (10s)
        @param error_screenshot_dir: directory will be used to store screenshots when test fails
        @param **options: extra keyword arguments will be forwarded directly to selenium driver
        """
        self.filename = filename
        self.baseuri = baseuri.rstrip('/') if baseuri else baseuri
        self.setUpFunc, self.tearDownFunc = self.findFixtureFunctions(fixtures)
        self.pmd = pmd
        self.timeit = timeit
        self.webdriver = driver
        self.options = options
        self.timeout = timeout
        self.encoding = encoding
        self.error_screenshot_dir = error_screenshot_dir
        self.window_size = window_size

    def run(self):
        """Start execution of selenium tests (within setUp and tearDown wrappers)"""
        logger.info('Selexe working on file %s' % self.filename)
        options = dict(self.options)
        if self.webdriver in self.webdriver_timeout_support:
            options['timeout'] = self.timeout + 10
        parser = self.parser_class.from_path(self.filename, encoding=self.encoding)
        driver = self.webdriver_classes[self.webdriver](**options)
        if self.window_size:
            width, height = self.window_size
            driver.set_window_size(width, height)
        logger.info('baseURI: %s' % self.baseuri)
        try:
            sd = self.driver_class(driver, self.baseuri, self.timeout)
            return self._wrapExecution(parser, sd)
        finally:
            driver.quit()

    def _wrapExecution(self, seleniumParser, sd):
        """Wrap execution of selenium tests in setUp and tearDown functions if available"""
        if self.setUpFunc:
            logger.info("Calling setUp()")
            self.setUpFunc(sd)
            logger.info("setUp() finished")
            # remove all verification errors possibly generated during setUpFunc()
            sd.clean_verification_errors()

        try:
            return self._executeSelenium(seleniumParser, sd)
        except:
            if self.error_screenshot_dir:
                path = os.path.join(self.error_screenshot_dir, time.strftime('%Y%m%d.%H%M%S.png'))
                sd.save_screenshot(path)
                logger.error('Screenshot saved to %s' % path)
            if self.pmd:
                exc = sys.exc_info()
                pdb.post_mortem(exc[2])
            else:
                raise
        finally:
            if self.tearDownFunc:
                logging.info("Calling tearDown()")
                self.tearDownFunc(sd)
                logger.info("tearDown() finished")

    def _execute_timeit(self, sd, command, target, value):
        time = timeit.timeit(functools.partial(sd, command, target, value), number=1)
        logger.info("Executed in %f sec" % (time))

    def _execute_command(self, sd, command, target, value):
        sd(command, target, value)

    def _executeSelenium(self, seleniumParser, sd):
        """Execute the actual selenium statements found in *sel file"""
        execute = self._execute_timeit if self.timeit else self._execute_command
        for baseuri, command, target, value in seleniumParser:
            if not self.baseuri and baseuri and baseuri != sd.base_url:
                logger.info("BaseURI: %s" % baseuri)
                sd.base_url = baseuri
            try:
                execute(sd, command, target, value)
            except:
                logger.error('Command %s(%r, %r) failed on \'%s\'.' % (command, target, value, sd.driver.current_url))
                raise
        return sd.verification_errors
        
    @staticmethod
    def findFixtureFunctions(modulePath=None):
        if hasattr(modulePath, '__iter__') and all(callable(i) for i in modulePath):
            return modulePath[0], modulePath[1]
        if callable(modulePath):
            return modulePath, None

        if modulePath == DEFAULT_FIXTURES_FILE and not os.path.exists(DEFAULT_FIXTURES_FILE):
            # The default fixtures file could be missing, then just no fixtures will be used
            modulePath = None
        elif modulePath and not os.path.exists(modulePath):
            # non-default fixtures files must exist, else raise an exception!
            raise SelexeError('Cannot find selexe fixture module "%s"')

        if modulePath:
            path, moduleWithExt = os.path.split(os.path.realpath(modulePath))
            module = os.path.splitext(moduleWithExt)[0]
            if path and not path in sys.path:
                sys.path.append(path)
            mod = __import__(os.path.basename(module))
            setUpFunc = getattr(mod, 'setUp', None)
            tearDownFunc = getattr(mod, 'tearDown', None)
            if setUpFunc or tearDownFunc:
                logger.info('Using fixtures module %s (setUp: %s, tearDown: %s)' %
                            (modulePath, setUpFunc is not None, tearDownFunc is not None))
            else:
                logger.warning('Successfully imported fixtures module %s, but found no setUp or tearDown functions' %
                                modulePath)
        else:
            logger.info('Using no fixtures')
            setUpFunc, tearDownFunc = None, None
        return setUpFunc, tearDownFunc

findFixtureFunctions = SelexeRunner.findFixtureFunctions # backwards compatibility


if __name__ == '__main__':
    from cmdargs import parse_cmd_args
    (options, args) = parse_cmd_args()
    logging.basicConfig(level=options.logging)
    for selFilename in args:
        s = SelexeRunner(selFilename, baseuri=options.baseuri, pmd=options.pmd, fixtures=options.fixtures, timeit=options.timeit, driver=options.driver)
        res = s.run()
        if res:
            sys.stderr.write("\nVerification errors in %s: %s\n" % (selFilename, res))
    sys.exit(1)
