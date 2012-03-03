import logging, time, re, types
###
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.alert import Alert
from fnmatch import fnmatchcase as compare
from userfunctions import Userfunctions

#globals
# time until timeout in seconds
TIMEOUT = 20

def create_verify(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'verify*' function.
    """
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        if matches(val, res):
            return True
        else:
            verificationError = 'Value "%s" did not match "%s"' % (str(res), str(val))
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
        res, val = func(self, *args, **kw)
        if not matches(val, res):
            return True
        else:
            verificationError = 'Value "%s" did not match "%s"' % (str(res), str(val))
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
        res, val = func(self, *args, **kw)
        assert matches(val, res)
    return wrap_func


def create_assertNot(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'assertNot*' function.
    """
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        assert not matches(val, res)
    return wrap_func


def create_waitFor(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'waitFor*' function.
    """
    def wrap_func(self, *args, **kw):
        for i in range (TIMEOUT):
            try:
                res, val = func(self, *args, **kw)
                assert matches(val, res)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d seconds" % TIMEOUT)
    return wrap_func


def create_waitForNot(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'waitForNot*' function.
    """
    def wrap_func(self, *args, **kw):
        for i in range (TIMEOUT):
            try:
                res, val = func(self, *args, **kw)
                assert not matches(val, res)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d seconds" % TIMEOUT)
    return wrap_func


def create_store(func):
    """
    Decorator to convert a test method of class WebDriver (starting with 'wd_get*') into a Selenium
    'store*' function.
    """
    def wrap_func(self, *args, **kw):
        res, val = func(self, *args, **kw)
        self.storedVariables[val] = res
    return wrap_func


def create_additional_methods(cls):
    """
    A class decorator to apply all available wrapping decorators to those methods in class WebDriver
    starting with 'wd_get*'
    """
    PREFIX = 'wd_get'
    lstr = len(PREFIX)
    for method in cls.__dict__.keys():
        if method.startswith(PREFIX):
            postfix = method[lstr:]
            #for sel_prefix in []:


            setattr(cls, 'wd_verify' + postfix, create_verify(cls.__dict__[method]))
            setattr(cls, 'wd_verifyNot' + postfix, create_verifyNot(cls.__dict__[method]))
            setattr(cls, 'wd_assert' + postfix, create_assert(cls.__dict__[method]))
            setattr(cls, 'wd_assertNot' + postfix, create_assertNot(cls.__dict__[method]))
            setattr(cls, 'wd_waitFor' + postfix, create_waitFor(cls.__dict__[method]))
            setattr(cls, 'wd_waitForNot' + postfix, create_waitForNot(cls.__dict__[method]))
            setattr(cls, 'wd_store' + postfix, create_store(cls.__dict__[method]))
    return cls

####################################################################################################

@create_additional_methods
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

    def __call__(self, command, target, value=None):
        """Make an actual call to a selenium action method.
        Examples for methods are 'verifyText', 'assertText', 'waitForText', etc., so methods that are
        typically available in the selenium IDE.
        Most methods are dynamically created through decorator functions (from 'wd_get*-methods) and hence are
        dynamically looked up in the class dictionary.
        """
        logging.info('%s("%s", "%s")' % (command, target, value))
        try:
            func = getattr(self, 'wd_'+command)
        except AttributeError:
            raise NotImplementedError('no proper function for sel command "%s" implemented' % command)
        v_target = self.expandVariables(target)
        v_value  = self.expandVariables(value) if value else value
        func(v_target, v_value)
        
    def importUserFunctions(self):
        funcNames = [key for (key, value) in Userfunctions.__dict__.iteritems() if isinstance(value, types.FunctionType)]
        usr = Userfunctions(self)
        for funcName in funcNames:
            setattr(self, funcName, getattr(usr, funcName))

    sel_var_pat = re.compile(r'\$({\w+})')
    def expandVariables(self, s):
        """expand variables contained in selenese files
        Multiple variables can be contained in a string from a selenese file. The format is ${<VARIABLENAME}.
        In order to use Python's formatting functionality all that needs to be done is to remove
        the dollar char from the curly braces as a preparational step. Then formatting is just done
        by providing a dictionary with all currently stored variables.
        """
        s_no_dollars = self.sel_var_pat.sub(r'\1', s)
        return s_no_dollars.format(**self.storedVariables)


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
        """click onto a target (e.g. a button) and wait until the browser receives a new page
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        find_target(self.driver, target).click()

    def wd_click(self, target, value=None):
        find_target(self.driver, target).click()
    
    def wd_select(self, target, value):
        target_elem = find_target(self.driver, target)
        tag, tvalue = _tag_and_value(value)
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
        ttype, ttarget = _tag_and_value(target)
        if (ttype != 'name' and ttarget != 'null'):
            raise NotImplementedError('only window locators with the prefix "name=" are supported currently')
        if ttarget == "null":
            ttarget = 0
        self.driver.switch_to_window(ttarget)

    def wd_selectFrame(self, target, value):
        webElem = find_target(self.driver, target)
        self.driver.switch_to_frame(webElem)

    ###
    # Section 2: All get*-statements (from which all other methods are created dynamically via decorators)
    ###

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
            return driver.find_element_by_id(ttarget)
        except:
            return driver.find_element_by_name(ttarget) 
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
    elif ttype in ['id', None]:
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
        pat = translateWilcardToRegex(pat)
        return re.search(pat, text) 
    
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
    

