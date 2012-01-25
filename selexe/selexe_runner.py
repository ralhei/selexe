#!/usr/bin/env python

import sys, os, logging
###
from selenium import webdriver
###
from parse_sel import SeleniumParser
from webdriver_commands import Webdriver


class SelexeError(Exception):
    """Custom Selexe error class"""
    pass


class SelexeRunner(object):
    """
    Selenium file execution class
    """
    def __init__(self, filename, baseuri=None, fixtures=None, pmd=False):
        self.filename = filename
        self.baseuri= baseuri
        self.setUpFunc, self.tearDownFunc = findFixtureFunctions(fixtures)
        self.pmd = pmd

    def run(self):
        """Start execution of selenium tests (within setUp and tearDown wrappers)"""
        logging.info('Selexe working on file %s' % self.filename)
        fp = open(self.filename)
        seleniumParser = SeleniumParser(fp)
        exe = self._wrapExecution if not self.pmd else self._wrapExecutionPDB
        driver = webdriver.Firefox()
        try:
            driver.implicitly_wait(30)
            wdc = Webdriver(driver, self.baseuri or seleniumParser.baseuri)
            return exe(seleniumParser, wdc)
        finally:
            driver.quit()

    def _wrapExecutionPDB(self, seleniumParser, wdc):
        """Run selenium execution, jump into post-mortem debugger in case of an error"""
        try:
            self._wrapExecution(seleniumParser, wdc)
        except:
            import pdb
            exc = sys.exc_info()
            pdb.post_mortem(exc[2])

    def _wrapExecution(self, seleniumParser, wdc):
        """Wrap execution of selenium tests in setUp and tearDown functions if available"""
        if self.setUpFunc:
            self.setUpFunc(wdc)
        try:
            return self._executeSelenium(seleniumParser, wdc)
        finally:
            if self.tearDownFunc:
                self.tearDownFunc(wdc)

    def _executeSelenium(self, seleniumParser, wdc):
        """Execute the actual selenium statements found in *sel file"""
        for command, target, value in seleniumParser:
            logging.info('%s("%s", "%s")' % (command, target, value))
            try:
                func = getattr(wdc, 'wd_'+command)
            except AttributeError:
                raise NotImplementedError('no proper function for sel command "%s" implemented' % command)
            func(target, value)
        return wdc.getVerificationErrors()


def findFixtureFunctions(modulePath=None):
    if not modulePath:
        modulePath = 'selexeFixtures.py' if os.path.exists('selexeFixtures.py') else None
    else:
        if not os.path.exists(modulePath):
            raise SelexeError('Cannot find selexe fixture module "%s"')
    if modulePath:
        path, moduleWithExt = os.path.split(modulePath)
        module = os.path.splitext(moduleWithExt)[0]
        if path and not path in sys.path:
            sys.path.append(path)
        mod = __import__(os.path.basename(module))
        setUpFunc = getattr(mod, 'setUp', None)
        tearDownFunc = getattr(mod, 'tearDown', None)
        if setUpFunc or tearDownFunc:
            logging.debug('Using fixtures module %s (setUp: %s, tearDown: %s)' %
                          (modulePath, setUpFunc is not None, tearDownFunc is not None))
        else:
            logging.warning('Successfully imported fixtures module %s, but found no setUp or tearDown functions' %
                            modulePath)
    else:
        logging.debug('Using no fixtures')
        setUpFunc, tearDownFunc = None, None
    return setUpFunc, tearDownFunc


if __name__ == '__main__':
    from cmdargs import parse_cmd_args
    (options, args) = parse_cmd_args()
    logging.basicConfig(level=options.logging)
    for selFilename in args:
        s = SelexeRunner(selFilename, baseuri=options.baseuri, pmd=options.pmd, fixtures=options.fixtures)
        print s.run()
