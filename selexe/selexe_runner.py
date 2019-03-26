#!/usr/bin/env python

import sys
import os
import os.path
import logging
import functools
import time
import timeit
import six

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from .parse_sel import SeleniumParser
from .selenium_driver import SeleniumDriver

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
    }
    webdriver_useragents = {}

    def __init__(self, filename, baseuri=None, fixtures=None, pmd=False, timeit=False, driver='firefox',
                 window_size=(1280, 720), encoding='utf-8', timeout=30000, error_screenshot_dir=None, useragent=None,
                 **options):
        """
        @param filename: Selenium IDE file
        @param baseuri: base url for selenium tests
        @param fixtures: 2-tuple of callable fixtures or module path with global SetUp and tearDown functions
        @param pmd: launches pdb on fail if True, defaults to False
        @param timeit: logs time taken by every command on logging level INFO if True, defaults to False
        @param driver: selenium driver as string, defaults to 'firefox'
        @param window_size: desired window size as (width, height) tuple, defaults to None
        @param encoding: encoding will be used by Selenium IDE test parser
        @param timeout: maximum milliseconds will be waited for every command before failing, defaults to 30000 (30s)
        @param error_screenshot_dir: directory will be used to store screenshots when test fails
        @param **options: extra keyword arguments will be forwarded directly to selenium driver
        """
        self.filename = filename
        self.baseuri = baseuri.rstrip('/') if baseuri else baseuri
        self.setUpFunc, self.tearDownFunc = self.findFixtureFunctions(fixtures)
        self.pmd = pmd
        self.timeit = timeit
        self.webdriver = driver
        self.useragent = useragent

        self.timeout = timeout
        self.encoding = encoding
        self.error_screenshot_dir = error_screenshot_dir
        self.window_size = window_size

        self.options = self._default_options()
        self.options.update(options)

    def run(self):
        """Start execution of selenium tests (within setUp and tearDown wrappers)"""
        logger.info('Selexe working on file %s' % self.filename)
        parser = self.parser_class.from_path(self.filename, encoding=self.encoding)
        # Note: some RemoteWebDriver-based drivers accept an `timeout` parameter but it's *absolutely unused*
        driver = self.webdriver_classes[self.webdriver](**self.options)
        width, height = self.window_size
        driver.set_window_size(width, height)
        logger.info('baseURI: %s' % self.baseuri)
        try:
            sd = self.driver_class(driver, self.baseuri, self.timeout)
            return self._wrapExecution(parser, sd)
        finally:
            driver.quit()

    def _default_options(self):
        """
        Generate capabilities object for current webdriver

        @return: capabilities object
        """

        useragent = self.useragent or self.webdriver_useragents.get(self.webdriver)
        options = {}
        if useragent:
            if self.webdriver == 'phantomjs':
                capabilities = DesiredCapabilities.PHANTOMJS.copy()
                capabilities['phantomjs.page.settings.userAgent'] = useragent
                options['desired_capabilities'] = capabilities
            elif self.webdriver == 'firefox':
                profile = webdriver.FirefoxProfile()
                profile.set_preference('general.useragent.override', useragent)
                options['firefox_profile'] = profile
            elif self.webdriver == 'chrome':
                chrome_options = webdriver.ChromeOptions()
                chrome_options.add_argument('--user-agent=\'%s\'' % useragent.replace("'", "'\\''"))
                options['chrome_options'] = chrome_options
            else:
                logger.exception('Custom useragent couldn\'t be set on %s driver.' % self.webdriver)
        return options

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
        except BaseException as e:
            if self.error_screenshot_dir:
                path = os.path.join(self.error_screenshot_dir, time.strftime('%Y%m%d.%H%M%S.png'))
                sd.save_screenshot(path)
                logger.error('Screenshot saved to %s' % path)
            if self.pmd:
                tb = sys.exc_info()[2]
                try:
                    import ipdb as pdb
                except ImportError:
                    import pdb
                pdb.post_mortem(tb)
            else:
                raise
        finally:
            if self.tearDownFunc:
                logging.info("Calling tearDown()")
                self.tearDownFunc(sd)
                logger.info("tearDown() finished")

    def _executeSelenium(self, seleniumParser, sd):
        """Execute the actual selenium statements found in *sel file"""
        for baseuri, command, target, value in seleniumParser:
            if not self.baseuri and baseuri and baseuri != sd.baseuri:
                logger.info("BaseURI: %s" % baseuri)
                sd.baseuri = baseuri
            try:
                if self.timeit:
                    time = timeit.timeit(functools.partial(sd, command, target, value), number=1)
                    logger.info("Executed in %f sec" % time)
                else:
                    sd(command, target, value)
            except:
                logger.error('Command %s(%r, %r) failed on \'%s\'.' % (command, target, value, sd.driver.current_url))
                raise
        return sd.verification_errors

    @staticmethod
    def findFixtureFunctions(modulePath=None):
        """
        Get setUp and tearDown functions in module whose path is given or, if single or pair of callables are given,
        return them.

        @param modulePath: path, callable or pair of callables.
        @return: pair of callables, callable and None, or (None, None).
        """
        # Pair of callables
        if hasattr(modulePath, '__iter__') and all(callable(i) for i in modulePath):
            return modulePath[0], modulePath[1]

        # Callable
        if callable(modulePath):
            return modulePath, None

        # Path
        if isinstance(modulePath, six.string_types):
            directory, filename = os.path.split(os.path.realpath(modulePath))
            modulename, extension = os.path.splitext(filename)
            if directory and directory not in sys.path:
                sys.path.append(directory)
            module = __import__(modulename)
            setUpFunc = getattr(module, 'setUp', None)
            tearDownFunc = getattr(module, 'tearDown', None)
            if setUpFunc or tearDownFunc:
                logger.info('Using fixtures module %s (setUp: %s, tearDown: %s)' %
                            (modulePath, setUpFunc is not None, tearDownFunc is not None))
            else:
                logger.warning('Successfully imported fixtures module %s, but found no setUp or tearDown functions' %
                               modulePath)
            return setUpFunc, tearDownFunc

        # Nothing
        logger.info('Using no fixtures')
        return None, None


findFixtureFunctions = SelexeRunner.findFixtureFunctions  # backwards compatibility
