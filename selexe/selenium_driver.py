import logging, time, re, types
###
from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException, NoAlertPresentException, \
UnexpectedTagNameException, NoSuchFrameException, NoSuchAttributeException 
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from fnmatch import fnmatchcase as globmatchcase
from userfunctions import Userfunctions
from html2text import html2text

#globals
# time until timeout in milliseconds
TIMEOUT = 20000
# time for searching for a html element in seconds
IMPLICITLY_WAIT = 0



def create_get_is(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'get*' function.
    """
    def wrap_func_get(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        return data
    
    def wrap_func_is(self, *args, **kw):
        data = func(self, *args, **kw)
        return data
    
    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}     
    return wrap_func[var]


def create_verify(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'verify*' function.
    """
    def wrap_func_get(self, *args, **kw):
        try:
            reference, data = func(self, *args, **kw)
            assert self._matches(reference, data)
            return True
        except NoAlertPresentException:
            verificationError = "There were no alerts or confirmations"
        except AssertionError:
            verificationError = 'Actual value "%s" did not match "%s"' % (str(data), str(reference))
        logging.error(verificationError)
        self.verificationErrors.append(verificationError)        
        return False
    
    def wrap_func_is(self, *args, **kw):
        try:
            assert func(self, *args, **kw)
            return True
        except NoAlertPresentException:
            verificationError = "There were no alerts or confirmations"
        except AssertionError:
            verificationError = "false"
        logging.error(verificationError)
        self.verificationErrors.append(verificationError)        
        return False
    
    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}     
    return wrap_func[var]


def create_verifyNot(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium '
    verifyNot*' function.
    """
    def wrap_func_get(self, *args, **kw):
        try:
            reference, data = func(self, *args, **kw)
            assert not self._matches(reference, data)
            return True
        except NoAlertPresentException:
            verificationError = "There were no alerts or confirmations"
        except AssertionError:
            verificationError = 'Actual value "%s" did match "%s"' % (str(data), str(reference))
        logging.error(verificationError)
        self.verificationErrors.append(verificationError)        
        return False
    
    def wrap_func_is(self, *args, **kw):
        try:
            assert not func(self, *args, **kw)
            return True
        except NoAlertPresentException:
            verificationError = "There were no alerts or confirmations"
        except AssertionError:
            verificationError = "true"
        logging.error(verificationError)
        self.verificationErrors.append(verificationError)        
        return False

    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}     
    return wrap_func[var]

   
def create_assert(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'assert*' function.
    """
    def wrap_func_get(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        assert self._matches(reference, data)

    def wrap_func_is(self, *args, **kw):
        assert func(self, *args, **kw)
        
    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}     
    return wrap_func[var]


def create_assertNot(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'assertNot*' function.
    """
    def wrap_func_get(self, *args, **kw):
        reference, data = func(self, *args, **kw)
        assert not self._matches(reference, data)
    
    def wrap_func_is(self, *args, **kw):
        assert not func(self, *args, **kw)
        
    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}    
    return wrap_func[var]


def create_waitFor(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'waitFor*' function.
    """
    def wrap_func_get(self, *args, **kw):
        timeout = kw.pop('timeout', TIMEOUT)
        for i in range (timeout / 1000):
            try:
                reference, data = func(self, *args, **kw)
                assert self._matches(reference, data)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d ms" % timeout)

    def wrap_func_is(self, *args, **kw):
        timeout = kw.pop('timeout', TIMEOUT)
        for i in range (timeout / 1000):
            try:
                assert func(self, *args, **kw)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d ms" % timeout)
    
    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}     
    return wrap_func[var]

def create_waitForNot(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'waitForNot*' function.
    """
    def wrap_func_get(self, *args, **kw):
        timeout = kw.pop('timeout', TIMEOUT)
        for i in range (timeout / 1000):
            try:
                reference, data = func(self, *args, **kw)
                assert not self._matches(reference, data)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d ms" % timeout)
        

    def wrap_func_is(self, *args, **kw):
        timeout = kw.pop('timeout', TIMEOUT)
        for i in range (timeout / 1000):
            try:
                assert not func(self, *args, **kw)
                break
            except AssertionError:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out after %d ms" % timeout)
        
    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}     
    return wrap_func[var]


def create_store(func, var):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'store*' function.
    """
    def wrap_func_get(self, *args, **kw):
        var, data = func(self, *args, **kw)
        self.storedVariables[var] = data
        
    def wrap_func_is(self, *args, **kw):
        data = func(self, *args, **kw)
        self.storedVariables[args[1]] = str(data).lower()
        
    wrap_func = {"get" : wrap_func_get, "is" : wrap_func_is}     
    return wrap_func[var]


def create_selenium_methods(cls):
    """
    Class decorator to setup all available wrapping decorators to those methods in class SeleniumCommander
    starting with 'wd_SEL*'
    """

    def decorate_method(cls, methodName, new_prefix, prefix, decoratorFunc):
        """
        This method double-decorates a generic webdriver command.
        1. Decorate it with one of the create_get, create_verify... decorators.
           These decorators convert the generic methods into a real selenium commands.
        2. Decorate with the 'seleniumcommand' method decorator.
           This wrapper expands selenium variables in the 'target' and 'value' and
           does the logging.
        """
        seleniumMethodName = new_prefix + methodName[len(prefix):]
        wrappedMethod = decoratorFunc(cls.__dict__[methodName], variants[prefix])
        wrappedMethod.__name__ = seleniumMethodName
        setattr(cls, seleniumMethodName, seleniumcommand(wrappedMethod))
        
    PREFIX1 = 'SEL_get_'
    PREFIX2 = 'SEL_is_'
    variants = {PREFIX1 : "get" , PREFIX2 : "is"}
    
    for prefix in variants.keys():
        for methodName in cls.__dict__.keys():    
            if methodName.startswith(prefix):
                decorate_method(cls, methodName, variants[prefix], prefix, create_get_is)
                decorate_method(cls, methodName, 'verify', prefix, create_verify)
                decorate_method(cls, methodName, 'verifyNot', prefix, create_verifyNot)
                decorate_method(cls, methodName, 'assert', prefix, create_assert)
                decorate_method(cls, methodName, 'assertNot', prefix, create_assertNot)
                decorate_method(cls, methodName, 'waitFor', prefix, create_waitFor)
                decorate_method(cls, methodName, 'waitForNot', prefix, create_waitForNot)
                decorate_method(cls, methodName, 'store', prefix, create_store)    
    return cls        
    

def seleniumcommand(method):
    """Method decorator for selenium commands in SeleniumCommander class.
    Wraps all available selenium commands for expand selenium variables in 'target' and 'value'
    arguments.
    """
    def seleniumMethod(self, target, value=None, log=True, **kw):
        if log:
            logging.info('%s(%r, %r)' % (method.__name__, target, value))
        v_target = self._expandVariables(target)
        v_value  = self._expandVariables(value) if value else value
        return method(self, v_target, v_value, **kw)
    #
    seleniumMethod.__name__ = method.__name__
    seleniumMethod.__doc__ = method.__doc__
    return seleniumMethod


def create_aliases(cls):
    for methodName in cls.__dict__.keys():    
        if re.match(r"(verifyNot|assertNot|waitForNot)\w+Present", methodName):
            method = getattr(cls, methodName)
            def aliasMethod(self, target, value=None):
                return method(self, target, value)
            alias = methodName.replace("Not", "").replace("Present", "NotPresent")
            setattr(cls, alias, aliasMethod)
    return cls


####################################################################################################
@create_aliases
@create_selenium_methods
class SeleniumDriver(object):
    def __init__(self, driver, base_url):
        self.driver = driver
        self.driver.implicitly_wait(IMPLICITLY_WAIT)
        self.base_url = base_url
        self.initVerificationErrors()
        self._importUserFunctions()
        # 'storedVariables' is used through the 'create_store' decorator above to store values during a selenium run:
        self.storedVariables = {}
        
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
        Most methods are dynamically created through decorator functions (from 'wd_SEL*-methods) and hence are
        dynamically looked up in the class dictionary.
        """
        try:
            method = getattr(self, command)
        except AttributeError:
            raise NotImplementedError('no proper function for sel command "%s" implemented' % command)
        return method(target, value, **kw)

    def _importUserFunctions(self):
        funcNames = [key for (key, value) in Userfunctions.__dict__.iteritems() if isinstance(value, types.FunctionType)]
        usr = Userfunctions(self)
        for funcName in funcNames:
            setattr(self, funcName, getattr(usr, funcName))

    sel_var_pat = re.compile(r'\${([\w\d]+)}')
    def _expandVariables(self, s):
        """expand variables contained in selenese files
        Multiple variables can be contained in a string from a selenese file. The format is ${<VARIABLENAME}.
        Those are replaced from self.storedVariables via a re.sub() method.
        """
        return self.sel_var_pat.sub(lambda matchobj: self.storedVariables[matchobj.group(1)], s)


    ########################################################################################################
    # The actual translations from selenium-to-webdriver commands

    ###
    # Section 1: Interactions with the browser
    ###

    @seleniumcommand
    def open(self, target, value=None):
        """open a URL in the browser
        @param target: URL (string)
        @param value: <not used>
        """
        self.driver.get(self.base_url + target)

    @seleniumcommand
    def clickAndWait(self, target, value=None):
        """click onto a HTML target (e.g. a button) and wait until the browser receives a new page
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        self._find_target(target).click()

    @seleniumcommand
    def click(self, target, value=None):
        """Click onto a HTML target (e.g. a button)
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        self._find_target(target).click()

    @seleniumcommand
    def select(self, target, value):
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
        target_elem = self._find_target(target)
        tag, tvalue = self._tag_and_value(value)
        select = Select(target_elem)
        if tag in ['label', None]:
            tvalue = self._matchOptionText(target, tvalue)
            select.select_by_visible_text(tvalue)
        elif tag == 'value':
            tvalue = self._matchOptionValue(target, tvalue)
            select.select_by_value(tvalue)
        elif tag == 'id':
            target_elem = self._find_target(value)
            select.select_by_visible_text(target_elem.text)
        elif tag == 'index':
            select.select_by_index(int(tvalue))
        else:
            raise RuntimeError("Unknown option locator type: " + tag)
     
    def _matchOptionText(self, target, tvalue):
        for option in self._find_children(target):
            text = option.text
            if self._matches(tvalue, text):
                return text
        return tvalue
    
    def _matchOptionValue(self, target, tvalue):
        for option in self._find_children(target):
            value = option.get_attribute("value")
            if self._matches(tvalue, value):
                return value
        return tvalue
    
    def _find_children(self, target):
        ttype, ttarget = self._tag_and_value(target)
        if ttype == 'css':
            return self.driver.find_elements_by_css_selector(ttarget + ">*" )
        elif ttype == 'xpath':
            return self.driver.find_elements_by_xpath(ttarget + "/*")
        elif ttype == 'name':
            return self.driver.find_elements_by_xpath("//*[@name='" + ttarget + "']/*")
        elif ttype in ['id', None]:
            return self.driver.find_elements_by_xpath("//*[@id='" + ttarget + "']/*")
        else:
            raise UnexpectedTagNameException('no way to find child targets "%s"' % target)

    @seleniumcommand
    def type(self, target, value):
        """Type text into a HTML input field
        @param target: a string determining an input element in the HTML page
        @param value:  text to type
        """
        target_elem = self._find_target(target)
        target_elem.clear()
        target_elem.send_keys(value)

    @seleniumcommand
    def check(self, target, value=None):
        target_elem = self._find_target(target)
        if not target_elem.is_selected():
            target_elem.click()

    @seleniumcommand
    def uncheck(self, target, value=None):
        target_elem = self._find_target(target)
        if target_elem.is_selected():
            target_elem.click()

    @seleniumcommand
    def mouseOver(self, target, value=None):
        # Action Chains will not work with several Firefox Versions. Firefox Version 10.2 should be ok.
        target_elem = self._find_target(target)
        ActionChains(self.driver).move_to_element(target_elem).perform()

    @seleniumcommand
    def mouseOut(self, target, value=None):
        target_elem = self._find_target(target)
        actions = ActionChains(self.driver)
        actions.move_to_element(target_elem)
        actions.move_by_offset(target_elem.size["width"], 0).perform()

    @seleniumcommand
    def waitForPopUp(self, target, value):
        try:
            timeout = int(value)
        except (ValueError, TypeError):
            timeout = TIMEOUT
        if target in ("null", "0"):
            raise NotImplementedError('"null" or "0" are currently not available as pop up locators')
        for i in range(timeout / 1000):
            try:
                self.driver.switch_to_window(target)
                self.driver.switch_to_window(0)
                break
            except NoSuchWindowException:
                time.sleep(1)
        else:
            raise NoSuchWindowException("Timed out after %d ms" % timeout)

    @seleniumcommand
    def selectWindow(self, target, value):
        ttype, ttarget = self._tag_and_value(target)
        if (ttype != 'name' and ttarget != 'null'):
            raise NotImplementedError('Only window locators with the prefix "name=" are supported currently')
        if ttarget in ["null", ""]:
            ttarget = 0
        self.driver.switch_to_window(ttarget)

    @seleniumcommand
    def selectFrame(self, target, value):
        if target.startswith('relative='):
            if target[9:] == 'top':
                self.driver.switch_to_default_content()
            elif target[9:] == 'parent':
                raise NotImplementedError('Parent frames can not be located')
            else:
                raise NoSuchFrameException
        else:
            try:
                frame = int(target)
            except (ValueError, TypeError):
                frame = self._find_target(target)
            self.driver.switch_to_frame(frame)

    ###
    # Section 2: All wd_SEL*-statements (from which all other methods are created dynamically via decorators)
    ###
    
        
    def SEL_is_TextPresent(self, target, value):
        text = html2text(self.driver.page_source)
        return self._isContained(target, text)
    
    def SEL_is_ElementPresent(self, target, value):
        try:
            self._find_target(target)
            return True
        except NoSuchElementException:
            return False

    def SEL_get_Attribute(self, target, value):
        target, sep, attr = target.rpartition("@")
        attrValue = self._find_target(target).get_attribute(attr)
        if attrValue is None:
            raise NoSuchAttributeException
        return value, attrValue.strip()
        
    def SEL_get_Text(self, target, value):
        return value, self._find_target(target).text.strip()
        
    def SEL_get_Value(self, target, value):
        return value, self._find_target(target).get_attribute("value").strip()
    
    def SEL_get_XpathCount(self, target, value):
        count = len(self.driver.find_elements_by_xpath(target))
        return int(value), count

    def SEL_get_Alert(self, target, value=None):
        alert = Alert(self.driver)
        text = alert.text.strip() 
        alert.accept()
        return target, text
            
    def SEL_get_Confirmation(self, target, value=None):
        # Webdriver gives no opportunity to distinguish between alerts and confirmations.
        # Thus they are handled the same way here, although this does not reflect the exact behavior of the IDE
        return self.SEL_get_Alert(target, value)

    
    ################# Some helper Functions ##################


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
                return self.driver.find_element_by_id(ttarget)
            except:
                return self.driver.find_element_by_name(ttarget) 
        else:
            raise UnexpectedTagNameException('no way to find target "%s"' % target)
        
        
    def _matches(self, reference, data):
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
        # 1) plain equality comparison
        if type(reference) not in [str, unicode]:
            return data == reference 
        # 2) regexp
        elif reference.startswith('regexp:'):
            try:
                return data == re.match(reference[7:], data).group(0)
            except AttributeError:
                return False
        # 3) exact-tag:
        elif reference.startswith("exact:"):
            return data == reference[6:]
        # 4) glob/ wildcards
        else:
            if reference.startswith("glob:"):
                reference = reference[5:]
            # using the "fnmatch" module method "fnmatchcase" (aliased to globmatchcase) in order to handle wildcards.
            return globmatchcase(data, reference)
    
    
    def _isContained(self, pat, text):
        # 1) regexp
        if pat.startswith('regexp:'):
            return re.search(pat[7:], text) is not None
        # 2) exact-tag:
        elif pat.startswith("exact:"):
            return pat[6:] in text
        # 3) glob/ wildcards
        else:
            if pat.startswith("glob:"):
                pat = pat[5:]
            pat = self._translateWilcardToRegex(pat)
            return re.search(pat, text) is not None
        
    def _translateWilcardToRegex(self, wc):
        # !note: The IDE wildcards do not include [...] expressions.
        # escape metacharacters not used in wildcards
        metacharacters = ['\\', '.', '$','|','+','(',')', '[', ']']
        for char in metacharacters:
            wc = wc.replace(char, '\\' + char)
        # translate wildcard characters $ and *
        wc = re.sub(r"(?<!\\)\*", r".*", wc)
        wc = re.sub(r"(?<!\\)\?", r".", wc)
        return wc
    
    
