# -*- coding: iso-8859-1 -*-

import logging, time, re, types

###
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.alert import Alert
from htmlentitydefs import name2codepoint
from fnmatch import fnmatchcase as compare
from fnmatch import translate
from userfunctions import Userfunctions

#globals
# time until timeout in seconds
TIME = 20

def create_verify(func):
    #return func
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        verificationError = "Actual value \"" + str(res) + "\" did not match \"" + str(val) + "\""
        if matches(val, res):
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
        if not matches(val, res):
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
        assert matches(val, res)
    return wrap_func


def create_assertNot(func):
    #return func
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        assert not matches(val, res)
    return wrap_func


def create_waitFor(func):
    #return func
    def wrap_func(self, *args, **kw):
        for _i in range (TIME):
            try:
                res, val = func(self, *args, **kw)
                assert matches(val, res)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after " + str(TIME) + " seconds")
    return wrap_func


def create_waitForNot(func):
    #return func
    def wrap_func(self, *args, **kw):
        for _i in range (TIME):
            try:
                res, val = func(self, *args, **kw)
                assert not matches(val, res)
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
        self.driver.implicitly_wait(3)
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
        usr = Userfunctions(self)
        for funcName in funcNames:
            setattr(self, funcName, getattr(usr, funcName))
        
        
    ########################################################################################################
    # The actual translations from selenium-to-webdriver commands:

    def wd_open(self, target, value=None):
        print self.base_url + target
        self.driver.get(self.base_url + target)

    def wd_clickAndWait(self, target, value=None):
        find_target(self.driver, target).click()

    def wd_click(self, target, value=None):
        find_target(self.driver, target).click()
    
    def wd_select(self, target, value):
        target_elem = find_target(self.driver, target)
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
            target_elem = find_target(value)
            select.select_by_visible_text(target_elem.text)
        elif tag == 'index':
            select.select_by_index(int(tvalue))
        else:
            raise RuntimeError("Unknown option locator type: " + tag)
     
    def matchChildren(self, target, tvalue, method):
        for child in find_children(self.driver, target):
            res = {"text": child.text, "value": child.get_attribute("value")}
            if self.matches(tvalue, res[method]):
                return res[method]
        return tvalue
               
        
    def wd_type(self, target, value):
        target_elem = find_target(self.driver, target)
        target_elem.clear()
        target_elem.send_keys(value)
        
    def wd_check(self, target, value=None):
        target_elem = find_target(self.driver, target)
        if not target_elem.is_selected():
            target_elem.click()
    
    def wd_uncheck(self, target, value=None):
        target_elem = find_target(self.driver, target)
        if target_elem.is_selected():
            target_elem.click()
    
    def wd_mouseOver(self, target, value=None):
        target_elem = find_target(self.driver, target)
        self.action.move_to_element(target_elem).perform()

    def wd_mouseOut(self, target, value=None):
        self.action.move_by_offset(0, 0).perform()
    
    #### All get statements ####

    def wd_getTextPresent(self, target, value=None):
        if isContained(target, self.driver.page_source):
            return "True", "True"
        else: 
            return "False", "True"
        
    def wd_getElementPresent(self, target, value=None):
        try:
            find_target(self.driver, target)
            return "True", "True"
        except NoSuchElementException:
            return "False", "True"

    def wd_getAttribute(self, target, value):
        target, _sep, attr = target.rpartition("@") 
        return find_target(self.driver, target).get_attribute(attr), value
        
    def wd_getText(self, target, value):
        return find_target(self.driver, target).text, value
        
    def wd_getValue(self, target, value):
        return find_target(self.driver, target).get_attribute("value"), value
    
    def wd_getXpathCount(self, target, value):
        count = len(find_targets(self.driver, target))
        return str(count), value

    def wd_getAlert(self, target, value=None):
        alert = Alert(self.driver)
        text = alert.text
        alert.accept()
        return text, target
    
    def wd_getConfirmation(self, target, value=None):
        return self.wd_getAlert(target, value)
   
    def wd_waitForPopUp(self, target, value):
        try:
            _time = int(value)
        except ValueError:
            _time = TIME
        if target in ("null", "0"):
            raise NotImplementedError('"null" or "0" are currently not available as pop up locators')
        for i in range(_time):
            try:
                self.driver.switch_to_window(target)
                self.driver.switch_to_window(0)
                break
            except NoSuchWindowException:
                time.sleep(1)
        else:
            raise NoSuchWindowException('timed out')
        
            
    def wd_selectWindow(self, target, value):
        ttype, ttarget = self._tag_and_value(target)
        if (ttype != 'name' and ttarget != 'null'):
            raise NotImplementedError('only window locators with the prefix "name=" are supported currently')
        if ttarget == "null":
            ttarget = 0
        self.driver.switch_to_window(ttarget)
        
            
    
    ##### Aliases ####
    
    def wd_verifyTextNotPresent(self, target, value=None):
        return wd_verifyNotTextPresent(target, value)
    
    def wd_assertTextNotPresent(self, target, value=None):
        return wd_assertNotTextPresent(target, value)
    
    def wd_verifyElementNotPresent(self, target, value=None):
        return wd_verifyNotElementPresent(target, value)
    
    def wd_assertElementNotPresent(self, target, value=None):
        return wd_assertNotElementPresent(target, value)
    
    ########################################################################################################
    # Some helper methods

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


def _tag_and_value(tvalue):
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

def find_target(driver, target):
    ttype, ttarget = _tag_and_value(target)
    if ttype == 'css':
        return driver.find_element_by_css_selector(ttarget)
    if ttype == 'xpath':
        return driver.find_element_by_xpath(ttarget)
    elif ttype == 'id':
        return driver.find_element_by_id(ttarget)
    elif ttype == 'name':
        return driver.find_element_by_name(ttarget)
    elif ttype == 'link':
        return driver.find_element_by_link_text(ttarget)
    elif ttype == None:
        try:
            return driver.find_elements_by_id(ttarget)
        except:
            return driver.find_elements_by_name(ttarget) 
    else:
        raise RuntimeError('no way to find target "%s"' % target)

def find_targets(driver, target):
    ttype, ttarget = _tag_and_value(target)
    if ttype == 'css':
        return driver.find_elements_by_css_selector(ttarget)
    if ttype == 'xpath': 
        return driver.find_elements_by_xpath(ttarget)
    elif ttype == 'name':
        return driver.find_elements_by_name(ttarget)
    elif ttype == 'link':
        return driver.find_elements_by_link_text(ttarget)
    else:
        raise RuntimeError('no way to find targets "%s"' % target)
    

def find_children(driver, target):
    ttype, ttarget = _tag_and_value(target)
    if ttype == 'css':
        return driver.find_elements_by_css_selector(ttarget + ">*" )
    if ttype == 'xpath':
        return driver.find_elements_by_xpath(ttarget + "/*")
    elif ttype == 'name':
        return driver.find_elements_by_xpath("//*[@name='" + ttarget + "']//*")
    elif ttype == 'id':
        return driver.find_elements_by_xpath("//" + ttarget + "/*")
    else:
        raise RuntimeError('no way to find targets "%s"' % target)
    
    
def matches(pat, res):
    # remove trailing whitespaces of result string to match IDE specifications
    res = res.strip()

    ''' This function handles the three kinds of String-match Patterns which Selenium defines.
    This is done in order to compare the pattern "pat" against "res".
    1.) regexp: a regular expression
    2.) exact: a non-wildcard expression
    3.) glob: a (possible) wildcard expression. This is the standard
    
    see: http://release.seleniumhq.org/selenium-remote-control/0.9.2/doc/dotnet/Selenium.html
    '''
    # 1) regexp
    if re.match("regexp:", pat):
        try:
            return res == re.match(pat[7:], res).group(0)
        except AttributeError:
            return False
    # 2) exact
    elif re.match("exact:", pat):
        return res == pat[6:] 
    # 3) glob
    else:
        return compare(res, pat)  # using the "fnmatch" module method "fnmatchcase" in order to handle wildcards.


def isContained(pat, text):
    pat = unicode(pat)
    # 1) regexp
    if re.match("regexp:", pat):
        try:
            return re.search(pat[7:], text).group(0)
        except AttributeError:
            return False
    # 2) exact
    elif re.match("exact:", pat):
        return pat[6:] in text
    # 3) glob
    else:
        print translate(pat)
        pat = translateWilcardToRegex(pat)
        print pat
        return re.search(pat, text) 
    
def translateWilcardToRegex(wc):
    metacharacters = ['.','[',']','^','$','|','+','(',')','\\']
    for char in metacharacters:
        wc = wc.replace(char, '\\' + char)
    wc. 
    #wc = wc.replace("*", ".*").replace("?", ".").replace('[!', '[^')
    return wc

