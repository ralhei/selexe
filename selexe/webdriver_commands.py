# -*- coding: iso-8859-1 -*-

import logging, time, re, types

###
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.alert import Alert
from htmlentitydefs import name2codepoint
from fnmatch import fnmatch as compare
from userfunctions import Userfunctions 

#globals
# time until timeout in seconds
TIME = 10

def create_verify(func):
    #return func
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        verificationError = "Actual value \"" + str(res) + "\" did not match \"" + str(val) + "\""
        if self.seleniumMatch(res, val):
            return True
        else:
            logging.error(verificationError) 
            self.verificationErrors.append(verificationError)
            return False
    return wrap_func


def create_verifyNot(func):
    #return func
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        verificationError = "Actual value \"" + str(res) + "\" did match \"" + str(val) + "\""
        if not self.seleniumMatch(res, val):
            return True
        else: 
            logging.error(verificationError)
            self.verificationErrors.append(verificationError)
            return False
    return wrap_func


def create_assert(func):
    #return func
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        assert self.seleniumMatch(res, val)
    return wrap_func


def create_assertNot(func):
    #return func
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        assert not self.seleniumMatch(res, val)
    return wrap_func


def create_waitFor(func):
    #return func
    def wrap_func(self, *args, **kw):
        for _i in range (60):
            try:
                res, val = func(self, *args, **kw)
                assert self.seleniumMatch(res, val)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after " + str(TIME) + " seconds")
    return wrap_func


def create_waitForNot(func):
    #return func
    def wrap_func(self, *args, **kw):
        for _i in range (60):
            try:
                res, val = func(self, *args, **kw)
                assert not self.seleniumMatch(res, val)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after " + str(TIME) + " seconds")
    return wrap_func


def create_store(func):
    #return func
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        self.variables[val] = res
    return wrap_func


def create_additional_methods(cls):
    PREFIX = 'wd_get'
    lstr = len(PREFIX)
    for method in cls.__dict__.keys():
        if method.startswith(PREFIX):
            postfix = method[lstr:]
            setattr(cls, 'wd_verify' + postfix, create_verify(cls.__dict__[method]))
            setattr(cls, 'wd_verifyNot' + postfix, create_verifyNot(cls.__dict__[method]))
            setattr(cls, 'wd_assert' + postfix, create_assert(cls.__dict__[method]))
            setattr(cls, 'wd_assertNot' + postfix, create_assertNot(cls.__dict__[method]))
            setattr(cls, 'wd_waitFor' + postfix, create_waitFor(cls.__dict__[method]))
            setattr(cls, 'wd_waitForNot' + postfix, create_waitForNot(cls.__dict__[method]))
            setattr(cls, 'wd_store' + postfix, create_store(cls.__dict__[method]))
    return cls



@create_additional_methods
class Webdriver(object):
    def __init__(self, driver, base_url):
        self.driver = driver
        self.driver.implicitly_wait(0)
        self.base_url = base_url
        self.initVerificationErrors()
        self.variables = {}
        self.importUserFunctions()
        # Action Chains will not work with several Firefox Versions
        # Firefox Version 10.2 should be ok
        self.action = ActionChains(self.driver)
       

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
        func(self.preprocess(target), self.preprocess(value))
        
    def importUserFunctions(self):
        funcNames = [key for (key, value) in Userfunctions.__dict__.iteritems() if isinstance(value, types.FunctionType)]
        usr = Userfunctions()
        for funcName in funcNames:
            setattr(self, funcName, getattr(usr, funcName))
        
        
    ########################################################################################################
    # The actual translations from selenium-to-webdriver commands:

    def wd_open(self, target, value=None):
        self.driver.get(self.base_url + target)

    def wd_clickAndWait(self, target, value=None):
        self.driver.implicitly_wait(TIME)
        self._find_target(target).click()
        self.driver.implicitly_wait(0)

    def wd_click(self, target, value=None):
        self._find_target(target).click()
    
    def wd_select(self, target, value):
        target_elem = self._find_target(target)
        tag, tvalue = self._tag_and_value(value)
        select = Select(target_elem)
        ''' 
        label=labelPattern: matches options based on their labels, i.e. the visible text. (This is the default.)
            label=regexp:^[Oo]ther
        value=valuePattern: matches options based on their values.
            value=other
        id=id: matches options based on their ids.
            id=option1
        index=index: matches an option based on its index (offset from zero).
            index=2 '''
        if tag in ['label', None]:
            tvalue = self.matchChildren(target, tvalue, "text")
            select.select_by_visible_text(tvalue)
        elif tag == 'value':
            tvalue = self.matchChildren(target, tvalue, "value")
            select.select_by_value(tvalue)
        elif tag == 'id':
            target_elem = self._find_target(value)
            select.select_by_visible_text(target_elem.text)
        elif tag == 'index':
            select.select_by_index(int(tvalue))
        else:
            raise RuntimeError("Unknown option locator type: " + tag)
     
    def matchChildren(self, target, tvalue, method):
        for child in self._find_targets(target, method):
            res = {"text": child.text, "value": child.get_attribute("value")}
            if self.seleniumMatch(res[method], tvalue):
                return res[method]
        return tvalue
               
        
    def wd_type(self, target, value):
        target_elem = self._find_target(target)
        target_elem.clear()
        target_elem.send_keys(value)
        
    def wd_check(self, target, value=None):
        target_elem = self._find_target(target)
        if not target_elem.is_selected():
            target_elem.click()
    
    def wd_uncheck(self, target, value=None):
        target_elem = self._find_target(target)
        if target_elem.is_selected():
            target_elem.click()
    
    def wd_mouseOver(self, target, value=None):
        target_elem = self._find_target(target)
        self.action.move_to_element(target_elem).perform()

    def wd_mouseOut(self, target, value=None):
        self.action.move_by_offset(0, 0).perform()
    
    #### All assert statements ####

    def wd_getTextPresent(self, target, value=None):
        if target in self.driver.page_source:
            return "True", "True"
        else: 
            return "False", "True"
        
    def wd_getElementPresent(self, target, value=None):
        try:
            self._find_target(target)
            return "True", "True"
        except NoSuchElementException:
            return "False", "True"

    def wd_getText(self, target, value=None):
        return self._find_target(target).text, value
        
    def wd_getValue(self, target, value):
        return self._find_target(target).get_attribute("value"), value
    
    def wd_getXpathCount(self, target, value):
        count = len(self._find_targets(target))
        return str(count), value

    def wd_getAlert(self, target, value=None):
        alert = Alert(self.driver)
        text = alert.text
        alert.accept()
        return text, target
    
    def wd_getConfirmation(self, target, value=None):
        return self.wd_getAlert(target, value)
    
    def wd_switchToWindow(self, target, value=None):
        pass
    
    def wd_switchToFrame(self, target, value=None):
        pass
    
    ##### Redirection ####
    
    def wd_verifyTextNotPresent(self, target, value=None):
        return wd_verifyNotTextPresent(target, value)
    
    def wd_assertTextNotPresent(self, target, value=None):
        return wd_assertNotTextPresent(target, value)
    
    ########################################################################################################
    # Some helper methods

    def _tag_and_value(self, tvalue):
        # target can be e.g. "css=td.f_transfectionprotocol"
        s = tvalue.split('=', 1)
        tag, value = s if len(s) == 2 else (None, None)
        if not tag in ['css', 'id', 'name', 'link', 'label', "value", "index"]:
            # Older sel files do not specify a 'css' or 'id' prefix. Lets distinguish by inspecting 'target'
            # NOTE: This check is probably not complete here!!! Watch out for problems!!!
            value = tvalue
            if tvalue.startswith('//'):
                tag = 'xpath'
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
        elif ttype == None:
            try:
                return self.driver.find_elements_by_id(ttarget)
            except:
                return self.driver.find_elements_by_name(ttarget) 
        else:
            raise RuntimeError('no way to find target "%s"' % target)

    def _find_targets(self, target, children=False):
        ttype, ttarget = self._tag_and_value(target)
        if ttype == 'css':
            ttarget = (ttarget + ">*" if children else ttarget) 
            return self.driver.find_elements_by_css_selector(ttarget)
        if ttype == 'xpath':
            ttarget = (ttarget + "/*" if children else ttarget) 
            return self.driver.find_elements_by_xpath(ttarget)
        elif ttype == 'name':
            ttarget = ("" if children else ttarget) 
            return self.driver.find_elements_by_name(ttarget)
        elif ttype == 'link':
            ttarget = ("" if children else ttarget) 
            return self.driver.find_elements_by_link_text(ttarget)
        elif ttype == 'id':
            if not children:
                raise RuntimeError('no way to find targets "%s"' % target)
            return self.driver.find_elements_by_xpath("//" + ttarget + "/*")
        else:
            raise RuntimeError('no way to find targets "%s"' % target)
        
    def seleniumMatch(self, res, val):
        # remove trailing whitespaces of res to match IDE specifications
        res = res.strip()

        ''' This function handles the three kinds of String-match Patterns which Selenium defines.
        This is done in order to compare the pattern "val" against "res"
        1.) regexp: a regular expression
        2.) exact: a non-wildcard expression
        3.) glob: a (possible) wildcard expression. This is the standard
        
        see: http://release.seleniumhq.org/selenium-remote-control/0.9.2/doc/dotnet/Selenium.html
        '''
        # 1) regexp
        if re.match("regexp:", val):
            try:
                return res == re.match(val[7:], res).group(0)
            except AttributeError:
                return False
        # 2) exact
        elif re.match("exact:", val):
            return res == val[6:] 
        # 3) glob
        else:
            return compare(res, val)  # using the "fnmatch" module method "fnmatch" in order to handle wildcards.
        
    def preprocess(self, s):
        '''
        Variables have to be inserted and a few parser drawbacks have to be handled:
        1) the parser does not decode html entitys
        2) empty strings are given back as "None" by the parser so they have to be reverted
        3) the return value of the parser is BeautifulSoup.BeautifulSoup.NavigableString so
        so this has to be changed to a workable type (currently unicode)
        '''
        if not s:
            s =""
        else: 
            s = unicode(s) 
            s = self.htmlentitydecode(s)
            s = self.insertVariables(s)                
        return s
    
    def insertVariables(self, s):
        for var in self.variables.keys():
            s = s.replace("${" + var + "}", self.variables[var])
        return s
    
    def htmlentitydecode(self, s):
        return re.sub('&(%s);' % '|'.join(name2codepoint), lambda m: unichr(name2codepoint[m.group(1)]), s)
