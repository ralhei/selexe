import logging
###
from selenium.webdriver.support.ui import Select


def catch_assert(func):
    #return func
    def wrap_func(self, *args, **kw):
        try:
            func(self, *args, **kw)
        except AssertionError as e:
            self.verificationErrors.append(str(e))
    return wrap_func


def create_verify_methods(cls):
    PREFIX = 'wd_assert'
    lstr = len(PREFIX)
    for method in cls.__dict__.keys():
        if method.startswith(PREFIX):
            postfix = method[lstr:]
            setattr(cls, 'wd_verify'+postfix, catch_assert(cls.__dict__[method]))
    return cls



@create_verify_methods
class Webdriver(object):
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.initVerificationErrors()

    def initVerificationErrors(self):
        self.verificationErrors = []

    def getVerificationErrors(self):
        return self.verificationErrors[:]  # return a copy!

    def __call__(self, command, target, value=None):
        logging.info('%s("%s", "%s")' % (command, target, value))
        try:
            func = getattr(self, 'wd_'+command)
        except AttributeError:
            raise NotImplementedError('no proper function for sel command "%s" implemented' % command)
        func(target, value)

    ########################################################################################################
    # The actual translations from selenium-to-webdriver commands:

    def wd_open(self, target, value=None):
        self.driver.get(self.base_url + target)

    def wd_clickAndWait(self, target, value=None):
        self._find_target(target).click()

    def wd_select(self, target, value):
        target_elem = self._find_target(target)
        tag, tvalue = self._tag_and_value(value)
        if tag == 'label':
            Select(target_elem).select_by_visible_text(tvalue)
        else:
            raise NotImplementedError()

    def wd_type(self, target, value):
        target_elem = self._find_target(target)
        target_elem.clear()
        target_elem.send_keys(value)

    #### All assert statements ####

    def wd_assertTextPresent(self, target, value=None):
        assert target in self.driver.page_source, 'Text "%s" not found in page' % target

    def wd_assertText(self, target, value):
        assert self._find_target(target).text == value, '"%s" != "%s"' % (self._find_target(target).text, value)

    def wd_assertValue(self, target, value):
        assert self._find_target(target).get_attribute("value") == value, \
               '"%s" != "%s"' % (self._find_target(target).get_attribute("value"), value)

    def wd_assertElementPresent(self, target, value=None):
        # The following command raises an NoSuchElementException which we let through!
        self._find_target(target)

    ########################################################################################################
    # Some helper methods

    def _tag_and_value(self, tvalue):
        # target can be e.g. "css=td.f_transfectionprotocol"
        s = tvalue.split('=')
        tag, value = s if len(s) == 2 else (None, None)

        if not tag in ['css', 'id', 'name', 'link', 'label']:
            # Older sel files do not specify a 'css' or 'id' prefix. Lets distinguish by inspecting 'target'
            # NOTE: This check is probably not complete here!!! Watch out for problems!!!
            value = tvalue
            if tvalue.startswith('//'):
                tag = 'xpath'
            else:
                tag = 'id'
        return tag, value

    def _find_target(self, target):
        ttype, ttarget = self._tag_and_value(target)
        if ttype == 'css':
            return self.driver.find_element_by_css_selector(ttarget)
        if ttype == 'xpath':
            return self.driver.find_element_by_xpath(ttarget)
        elif ttype == 'id':
            return self.driver.find_element_by_id(ttarget)
        elif ttype == 'name':
            return self.driver.find_element_by_name(ttarget)
        elif ttype == 'link':
            return self.driver.find_element_by_link_text(ttarget)
        else:
            raise RuntimeError('no way to find target "%s"' % target)


