import logging, time, re, types
###
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from fnmatch import fnmatchcase as globmatchcase
from userfunctions import Userfunctions
from selenium.webdriver.remote.webelement import WebElement

#globals
# time until timeout in seconds
TIMEOUT = 20

def create_get(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'get*' function.
    """
    def wrap_func(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        return data
    return wrap_func


def create_verify(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'verify*' function.
    """
    def wrap_func(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        if matches(reference, data):
            return True
        else:
            verificationError = 'Value "%s" did not match "%s"' % (str(data), str(reference))
            logging.error(verificationError)
            self.verificationErrors.append(verificationError)
            return False
    return wrap_func


def create_verifyNot(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium '
    verifyNot*' function.
    """
    def wrap_func(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        if not matches(reference, data):
            return True
        else:
            verificationError = 'Value "%s" did not match "%s"' % (str(data), str(reference))
            logging.error(verificationError)
            self.verificationErrors.append(verificationError)
            return False
    return wrap_func


def create_assert(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'assert*' function.
    """
    def wrap_func(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        assert matches(reference, data)
    return wrap_func


def create_assertNot(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'assertNot*' function.
    """
    def wrap_func(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        assert not matches(reference, data)
    return wrap_func


def create_waitFor(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'waitFor*' function.
    """
    def wrap_func(self, *args, **kw):
        timeout = kw.pop('timeout', TIMEOUT)
        for i in range (timeout):
            try:
                reference, data = func(self, *args, **kw)
                assert matches(reference, data)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d seconds" % timeout)
    return wrap_func


def create_waitForNot(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'waitForNot*' function.
    """
    def wrap_func(self, *args, **kw):
        timeout = kw.pop('timeout', TIMEOUT)
        for i in range (timeout):
            try:
                reference, data = func(self, *args, **kw)
                assert not matches(reference, data)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d seconds" % timeout)
    return wrap_func


def create_store(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'store*' function.
    """
    def wrap_func(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        self.storedVariables[reference] = data
    return wrap_func



def create_selenium_methods(cls):
    """
    A class decorator to setup all available wrapping decorators to those methods in class WebDriver
    starting with 'wd_get*'
    """
    PREFIX = 'wd_SEL_'
    lstr = len(PREFIX)

    def decorate_method(cls, methodName, prefix, decoratorFunc):
        seleniumMethodName = prefix + methodName[lstr:]
        wrappedMethod = decoratorFunc(cls.__dict__[methodName])
        wrappedMethod.__name__ = seleniumMethodName
        setattr(cls, seleniumMethodName, wrappedMethod)

    for methodName in cls.__dict__.keys():
        if methodName.startswith(PREFIX):
            decorate_method(cls, methodName, 'wd_get', create_get)
            decorate_method(cls, methodName, 'wd_verify', create_verify)
            decorate_method(cls, methodName, 'wd_assert', create_assert)
            decorate_method(cls, methodName, 'wd_assertNot', create_assertNot)
            decorate_method(cls, methodName, 'wd_waitFor', create_waitFor)
            decorate_method(cls, methodName, 'wd_waitForNot', create_waitForNot)
            decorate_method(cls, methodName, 'wd_store', create_store)
    return cls

####################################################################################################

@create_selenium_methods
class Webdriver(object):
    def __init__(self, driver, base_url):
        self.driver = driver
        self.driver.implicitly_wait(3)
        self.base_url = base_url
        self.initVerificationErrors()
        # 'storedVariables' is used through the 'create_store' decorator above to store values during a selenium run:
        self.storedVariables = {}
        self.importUserFunctions()
        # Action Chains will not work with several Firefox Versions. Firefox Version 10.2 should be ok.
        self.action = ActionChains(self.driver)

    def initVerificationErrors(self):
        """reset list of verification errors"""
        self.verificationErrors = []

    def getVerificationErrors(self):
        """get (a copy) of all available verification errors so far"""
        return self.verificationErrors[:]  # return a copy!

    def __call__(self, command, target, value=None, **kw):
        """Make an actual call to a selenium action method.
        Examples for methods are 'verifyText', 'assertText', 'waitForText', etc., so methods that are
        typically available in the selenium IDE.
        Most methods are dynamically created through decorator functions (from 'wd_get*-methods) and hence are
        dynamically looked up in the class dictionary.
        """
        logging.info('%s(%r, %r)' % (command, target, value))
        try:
            func = getattr(self, 'wd_'+command)
        except AttributeError:
            raise NotImplementedError('no proper function for sel command "%s" implemented' % command)
        v_target = self.expandVariables(target)
        v_value  = self.expandVariables(value) if value else value
        return func(v_target, v_value, **kw)
        
    def importUserFunctions(self):
        funcNames = [key for (key, value) in Userfunctions.__dict__.iteritems() if isinstance(value, types.FunctionType)]
        usr = Userfunctions(self)
        for funcName in funcNames:
            setattr(self, funcName, getattr(usr, funcName))

    sel_var_pat = re.compile(r'\$({\w+})')
    def expandVariables(self, s):
        """expand variables contained in selenese files
        Multiple variables can be contained in a string from a selenese file. The format is ${<VARIABLENAME}.
        Those are replaced from self.storedVariables via a re.sub() method.
        """
        #s_no_dollars = self.sel_var_pat.sub(r'\1', s)
        #return s_no_dollars.format(**self.storedVariables)
        return self.sel_var_pat.sub(lambda matchobj: self.storedVariables[matchobj.group(1)], s)


    ########################################################################################################
    # The actual translations from selenium-to-webdriver commands

    ###
    # Section 1: Interactions with the browser
    ###

    def wd_open(self, target, value=None):
        """open a URL in the browser
        @param target: URL (string)
        @param value: <not used>
        """
        self.driver.get(self.base_url + target)

    def wd_clickAndWait(self, target, value=None):
        """click onto a HTML target (e.g. a button) and wait until the browser receives a new page
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        find_target(self.driver, target).click()

    def wd_click(self, target, value=None):
        """Click onto a HTML target (e.g. a button)
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        find_target(self.driver, target).click()
    
    def wd_select(self, target, value):
        """In HTML select list (specified by 'target') select item (specified by 'value')
        'value' can have the following formats:
        label=labelPattern: matches options based on their labels, i.e. the visible text. (This is the default.)
            example: "label=regexp:^[Oo]ther"
        value=valuePattern: matches options based on their values.
            example: "value=other"
        id=id: matches options based on their ids.
            example: "id=option1"
        index=index: matches an option based on its index (offset from zero).
            example: "index=2"
        """
        target_elem = find_target(self.driver, target)
        tag, tvalue = tag_and_value(value)
        select = Select(target_elem)
        if tag in ['label', None]:
            tvalue = self.matchChildrenText(target, tvalue)
            select.select_by_visible_text(tvalue)
        elif tag == 'value':
            tvalue = self.matchChildrenValue(target, tvalue)
            select.select_by_value(tvalue)
        elif tag == 'id':
            target_elem = find_target(value)
            select.select_by_visible_text(target_elem.text)
        elif tag == 'index':
            select.select_by_index(int(tvalue))
        else:
            raise RuntimeError("Unknown option locator type: " + tag)
     
    def matchChildrenText(self, target, tvalue):
        for child in find_children(self.driver, target):
            text = child.text
            if matches(tvalue, text):
                return text
        return tvalue
    
    def matchChildrenValue(self, target, tvalue):
        for child in find_children(self.driver, target):
            value = child.get_attribute("value")
            if matches(tvalue, value):
                return value
        return tvalue

    def wd_type(self, target, value):
        """Type text into a HTML input field
        @param target: a string determining an input element in the HTML page
        @param value:  text to type
        """
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

    def wd_waitForPopUp(self, target, value):
        try:
            timeout = int(value)
        except ValueError:
            timeout = TIMEOUT
        if target in ("null", "0"):
            raise NotImplementedError('"null" or "0" are currently not available as pop up locators')
        for i in range(timeout):
            try:
                self.driver.switch_to_window(target)
                self.driver.switch_to_window(0)
                break
            except NoSuchWindowException:
                time.sleep(1)
        else:
            raise NoSuchWindowException('timed out')

    def wd_selectWindow(self, target, value):
        ttype, ttarget = tag_and_value(target)
        if (ttype != 'name' and ttarget != 'null'):
            raise NotImplementedError('only window locators with the prefix "name=" are supported currently')
        if ttarget == "null":
            ttarget = 0
        self.driver.switch_to_window(ttarget)

    def wd_selectFrame(self, target, value):
        webElem = find_target(self.driver, target)
        self.driver.switch_to_frame(webElem)

    ###
    # Section 2: All wd_SEL*-statements (from which all other methods are created dynamically via decorators)
    ###

    def wd_SEL_TextPresent(self, target, value=None):
        return True, isContained(target, self.driver.page_source)

    def wd_SEL_ElementPresent(self, target, value=None):
        try:
            find_target(self.driver, target)
            return True, True
        except NoSuchElementException:
            return True, False

    def wd_SEL_Attribute(self, target, value):
        target, sep, attr = target.rpartition("@")
        return value, find_target(self.driver, target).get_attribute(attr).strip()
        
    def wd_SEL_Text(self, target, value):
        return value, find_target(self.driver, target).text.strip()
        
    def wd_SEL_Value(self, target, value):
        return value, find_target(self.driver, target).get_attribute("value").strip()
    
    def wd_SEL_XpathCount(self, target, value):
        count = len(find_targets(self.driver, target))
        return value, str(count)

    def wd_SEL_Alert(self, target, value=None):
        alert = Alert(self.driver)
        text = alert.text.strip()
        alert.accept()
        return target, text
    
    def wd_SEL_Confirmation(self, target, value=None):
        return self.wd_getAlert(target, value)
   
    ##### Aliases ####
    
    def wd_verifyTextNotPresent(self, target, value=None):
        return self.wd_verifyNotTextPresent(target, value)
    
    def wd_assertTextNotPresent(self, target, value=None):
        return self.wd_assertNotTextPresent(target, value)
    
    def wd_verifyElementNotPresent(self, target, value=None):
        return self.wd_verifyNotElementPresent(target, value)
    
    def wd_assertElementNotPresent(self, target, value=None):
        return self.wd_assertNotElementPresent(target, value)
    

########################################################################################################


def tag_and_value(tvalue):
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
    ttype, ttarget = tag_and_value(target)
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
            return driver.find_element_by_id(ttarget)
        except:
            return driver.find_element_by_name(ttarget) 
    else:
        raise RuntimeError('no way to find target "%s"' % target)

def find_targets(driver, target):
    ttype, ttarget = tag_and_value(target)
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
    ttype, ttarget = tag_and_value(target)
    if ttype == 'css':
        return driver.find_elements_by_css_selector(ttarget + ">*" )
    if ttype == 'xpath':
        return driver.find_elements_by_xpath(ttarget + "/*")
    elif ttype == 'name':
        return driver.find_elements_by_xpath("//*[@name='" + ttarget + "']//*")
    elif ttype in ['id', None]:
        return driver.find_elements_by_xpath("//" + ttarget + "/*")
    else:
        raise RuntimeError('no way to find targets "%s"' % target)
    
    
def matches(reference, data):
    """Try to match data found in HTML with reference data
    @param reference: string containing the 'value' of a selenese command (can be plain text, regex, ...)
    @param data: string obtained from HTML via 'target'
    @result boolean

    This function handles the three kinds of String-match Patterns which Selenium defines.
    This is done in order to compare the pattern "pat" against "res".
    1) plain equality comparison
    2) regexp: a regular expression
    3) exact: a non-wildcard expression
    4) glob: a (possible) wildcard expression. This is the default (fallback) method if 1) and 2) don't apply
    
    see: http://release.seleniumhq.org/selenium-remote-control/0.9.2/doc/dotnet/Selenium.html
    """
    # 1) equality expression (works for booleans, integers, etc)
    if type(reference) not in [str, unicode]:
        return reference == data
    # 2) regexp
    elif reference.startswith('regexp:'):
        try:
            return data == re.match(reference[7:], data).group(0)
        except AttributeError:
            return False
    # 3) exact-tag:
    elif re.match("exact:", reference):
        return data == reference[6:]
    # 4) glob/wildcards
    else:
        # using the "fnmatch" module method "fnmatchcase" (aliased to globmatchcase) in order to handle wildcards.
        return globmatchcase(data, reference)


def isContained(pat, text):
    # 1) regexp
    if pat.startswith('regex:'):
        try:
            return text == re.search(pat[7:], text).group(0)
        except AttributeError:
            return False
    # 2) exact
    elif re.match("exact:", pat):
        return pat[6:] in text
    # 3) glob
    else:
        pat = translateWilcardToRegex(pat)
        return re.search(pat, text) is not None
    
def translateWilcardToRegex(wc):
    # escape metacharacters not used in wildcards
    metacharacters = ['\\', '.', '$','|','+','(',')']
    for char in metacharacters:
        wc = wc.replace(char, '\\' + char)
    # translate wildcard characters $ and *
    wc = re.sub(r"(?<!\\)\*", r".*", wc)
    wc = re.sub(r"(?<!\\)\?", r".", wc)
    # find brackets which should not be escaped
    nonEscapeBrackets = []
    for bracketPair in re.finditer(r"(?<!\\)\[[^\[]*?(?<!\\)\]", wc):
        nonEscapeBrackets.append(bracketPair.start())
        nonEscapeBrackets.append(bracketPair.end() - 1)
    # escape brackets 
    newWc = ""
    pos = 0
    for c in wc:
        if c in ['[',']'] and not pos in nonEscapeBrackets:
            c = "\\" + c
        newWc+=c
        pos+=1
    return newWc
    

