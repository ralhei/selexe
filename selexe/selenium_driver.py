import logging, time, re, types
###
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchAttributeException
from selenium.common.exceptions import UnexpectedTagNameException
from selenium.common.exceptions import NoSuchFrameException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from fnmatch import fnmatchcase as globmatchcase
from userfunctions import Userfunctions
from html2text import html2text



def create_get_or_is(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'is*' or 'get*' function.
    """
    def wrap_func(self, target, value=None):
        expectedResult, result = func(self, target, value=value)
        return result
    return wrap_func


def create_verify(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'verify*' function.
    """
    def wrap_func(self, target, value=None):
        try:
            expectedResult, result = func(self, target, value=value)  # can raise NoAlertPresentException
            assert self._matches(expectedResult, result)
            return True
        except NoAlertPresentException:
            verificationError = "There were no alerts or confirmations"
        except AssertionError:
            if result == False:
                # verifyTextPresent/verifyElementPresent only return True or False, so no proper comparison
                # can be made.
                verificationError = "false"
            else:
                verificationError = 'Actual value "%s" did not match "%s"' % (str(result), str(expectedResult))
        logging.error(verificationError)
        self.verificationErrors.append(verificationError)        
        return False
    return wrap_func


def create_verifyNot(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium '
    verifyNot*' function.
    """
    def wrap_func(self, target, value=None):
        try:
            expectedResult, result = func(self, target, value=value)  # can raise NoAlertPresentException
            assert not self._matches(expectedResult, result)
            return True
        except NoAlertPresentException:
            verificationError = "There were no alerts or confirmations"
        except AssertionError:
            if result == True:
                # verifyTextPresent/verifyElementPresent only return True or False, so no proper comparison
                # can be made.
                verificationError = "true"
            else:
                verificationError = 'Actual value "%s" did match "%s"' % (str(result), str(expectedResult))
        logging.error(verificationError)
        self.verificationErrors.append(verificationError)        
        return False
    return wrap_func


def create_assert(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'assert*' function.
    """
    def wrap_func(self, target, value=None):
        expectedResult, result = func(self, target, value=value)
        assert self._matches(expectedResult, result), \
                    'Actual value "%s" did not match "%s"' % (str(result), str(expectedResult))
    return wrap_func


def create_assertNot(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'assertNot*' function.
    """
    def wrap_func(self, target, value=None):
        expectedResult, result = func(self, target, value=value)
        assert not self._matches(expectedResult, result), \
                    'Actual value "%s" did match "%s"' % (str(result), str(expectedResult))
    return wrap_func


def create_waitFor(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'waitFor*' function.
    """
    def wrap_func(self, target, value=None):
        for i in range (self.num_repeats):
            try: 
                expectedResult, result = func(self, target, value=value)
                assert self._matches(expectedResult, result)
                break
            except AssertionError:
                time.sleep(self.poll)
        else:
            raise RuntimeError("Timed out after %d ms" % self.wait_for_timeout)
    return wrap_func


def create_waitForNot(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'waitForNot*' function.
    """
    def wrap_func(self, target, value=None):
        for i in range (self.num_repeats):
            try:
                expectedResult, result = func(self, target, value=value)
                assert not self._matches(expectedResult, result)
                break
            except AssertionError:
                time.sleep(self.poll)
        else:
            raise RuntimeError("Timed out after %d ms" % self.wait_for_timeout)
    return wrap_func


def create_store(func):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'store*' function.
    """
    def wrap_func(self, target, value=None):
        expectedResult, result = func(self, target, value=value)
        # for e.g. 'storeConfirmation' the variable name will be provided in 'target' (with 'value' being None),
        # for e.g. 'storeText' the variable name will be given in 'value' (target holds the element identifier)
        # The the heuristic is to use 'value' preferably over 'target' if available. Hope this works ;-)
        variableName = value or target
        self.storedVariables[variableName] = result
    return wrap_func


def create_selenium_methods(cls):
    """
    Class decorator to setup all available wrapping decorators to those methods in class SeleniumCommander
    starting with 'wd_SEL*'
    """
    GENERIC_METHOD_PREFIX = 'wd_SEL_'
    lstr = len(GENERIC_METHOD_PREFIX)

    def decorate_method(cls, methodName, prefix, decoratorFunc):
        """
        This method double-decorates a generic webdriver command.
        1. Decorate it with one of the create_get, create_verify... decorators.
           These decorators convert the generic methods into a real selenium commands.
        2. Decorate with the 'seleniumcommand' method decorator.
           This wrapper expands selenium variables in the 'target' and 'value' and
           does the logging.
        """
        seleniumMethodName = prefix + methodName[lstr:]
        wrappedMethod = decoratorFunc(cls.__dict__[methodName])
        wrappedMethod.__name__ = seleniumMethodName
        setattr(cls, seleniumMethodName, seleniumcommand(wrappedMethod))


    for methodName in cls.__dict__.keys():  # must loop over keys() as the dict gets modified while looping
        if methodName.startswith(GENERIC_METHOD_PREFIX):
            prefix = 'is' if methodName.endswith('Present') else 'get'
            decorate_method(cls, methodName, prefix, create_get_or_is)
            decorate_method(cls, methodName, 'verify', create_verify)
            decorate_method(cls, methodName, 'verifyNot', create_verifyNot)
            decorate_method(cls, methodName, 'assert', create_assert)
            decorate_method(cls, methodName, 'assertNot', create_assertNot)
            decorate_method(cls, methodName, 'waitFor', create_waitFor)
            decorate_method(cls, methodName, 'waitForNot', create_waitForNot)
            decorate_method(cls, methodName, 'store', create_store)
    return cls



def seleniumcommand(method):
    """
    Method decorator for selenium commands in SeleniumCommander class.
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
    """
    Creates aliases (like the IDE) for commands with prefixes "verifyNot", "assertNot" or "waitForNot" which were generated 
    from generic commands with suffix "Present". For the aliases the "Not" is moved away from the prefix and placed 
    before "Present"(most likely to increase readability), e.g. "verifyTextNotPresent" aliases to "verifyNotTextPresent".
    """
    for methodName in cls.__dict__.keys():  # must loop over keys() as the dict gets modified while looping
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
        self.base_url = base_url
        self.initVerificationErrors()
        self._importUserFunctions()
        self.setTimeoutAndPoll(20000, 0.5)
        # 'storedVariables' is used through the 'create_store' decorator above to store values during a selenium run:
        self.storedVariables = {}
      
    def initVerificationErrors(self):
        """reset list of verification errors"""
        self.verificationErrors = []

    def getVerificationErrors(self):
        """get (a copy) of all available verification errors so far"""
        return self.verificationErrors[:]  # return a copy!

    def __call__(self, command, target, value=None, **kw):
        """
        Make an actual call to a selenium action method.
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
        """
        Expand variables contained in selenese files.
        Multiple variables can be contained in a string from a selenese file. The format is ${<VARIABLENAME}.
        Those are replaced from self.storedVariables via a re.sub() method.
        """
        return self.sel_var_pat.sub(lambda matchobj: self.storedVariables[matchobj.group(1)], s)
    
    
    def setTimeoutAndPoll(self, timeout, poll):
        """
        Set attributes for commands starting with 'waitFor'. This is done initially.
        Attribute 'timeout' specifies the time until a waitFor command will time out in milliseconds.
        Attribute 'poll' specifies the time until the function inside a waitFor command is repeated in seconds.
        Attribute 'num_repeats' specifies the number of times the function inside a waitFor command is repeated.
        """
        self.wait_for_timeout = timeout
        self.poll = poll
        self.num_repeats = int(timeout / 1000 / poll)


    ########################################################################################################
    # The actual translations from selenium-to-webdriver commands

    ###
    # Section 1: Interactions with the browser
    ###

    @seleniumcommand
    def open(self, target, value=None):
        """
        Open a URL in the browser
        @param target: URL (string)
        @param value: <not used>
        """
        self.driver.get(self.base_url + target)

    @seleniumcommand
    def clickAndWait(self, target, value=None):
        """
        Click onto a HTML target (e.g. a button) and wait until the browser receives a new page
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        self._find_target(target).click()

    @seleniumcommand
    def click(self, target, value=None):
        """
        Click onto a HTML target (e.g. a button)
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        self._find_target(target).click()

    @seleniumcommand
    def select(self, target, value):
        """
        In HTML select list (specified by 'target') select item (specified by 'value')
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
            tvalue = self._matchOptionText(target_elem, tvalue)
            select.select_by_visible_text(tvalue)
        elif tag == 'value':
            tvalue = self._matchOptionValue(target_elem, tvalue)
            select.select_by_value(tvalue)
        elif tag == 'id':
            option = target_elem.find_element_by_id(tvalue)
            select.select_by_visible_text(option.text)
        elif tag == 'index':
            select.select_by_index(int(tvalue))
        else:
            raise RuntimeError("Unknown option locator type: " + tag)
     
    def _matchOptionText(self, target, tvalue):
        for option in target.find_elements_by_xpath("*"):
            text = option.text
            if self._matches(tvalue, text):
                return text
        return tvalue
    
    def _matchOptionValue(self, target, tvalue):
        for option in target.find_elements_by_xpath("*"):
            value = option.get_attribute("value")
            if self._matches(tvalue, value):
                return value
        return tvalue
        
    @seleniumcommand
    def type(self, target, value):
        """
        Types text into an input element.
        @param target: an element locator
        @param value: the text to type
        """
        target_elem = self._find_target(target)
        target_elem.clear()
        target_elem.send_keys(value)
        
  
    @seleniumcommand
    def check(self, target, value=None):
        """
        Checks a toggle-button (checkbox/radio)
        @param target: an element locator
        @param value: <not used>
        """
        target_elem = self._find_target(target)
        if not target_elem.is_selected():
            target_elem.click()

    @seleniumcommand
    def uncheck(self, target, value=None): 
        """
        Unchecks a toggle-button (checkbox/radio)
        @param target: an element locator
        @param value:  <not used>
        """
        target_elem = self._find_target(target)
        if target_elem.is_selected():
            target_elem.click()


    @seleniumcommand
    def mouseOver(self, target, value=None):
        """
        Simulates a user hovering a mouse over the specified element.
        @param target: an element locator
        @param value:  <not used>
        """
        target_elem = self._find_target(target)
          # Action Chains will not work with several Firefox Versions. Firefox Version 10.2 should be ok.
        ActionChains(self.driver).move_to_element(target_elem).perform()

  
    @seleniumcommand
    def mouseOut(self, target, value=None):
        """
        Simulates a user moving the mouse away from the specified element.
        @param target: an element locator
        @param value:  <not used>
        """
        target_elem = self._find_target(target)
        actions = ActionChains(self.driver)
        actions.move_to_element(target_elem)
        actions.move_by_offset(target_elem.size["width"] / 2 + 1, 0).perform()
        

    @seleniumcommand
    def waitForPopUp(self, target, value):
        """
        Waits for a popup window to appear and load up.
        @param target: the JavaScript window "name" of the window that will appear (not the text of the title bar).
        A target which is unspecified or specified as "null" is not supported currently.
        @param target: the JavaScript window ID of the window to select
        @param value: the timeout in milliseconds, after which the action will return with an error. If this value 
        is not specified, the default timeout will be used. See the setTimeoutAndPoll function.
        """
        try:
            timeout = int(value)
        except (ValueError, TypeError):
            timeout = self.wait_for_timeout
        if target in ("null", "0"):
            raise NotImplementedError('"null" or "0" are currently not available as pop up locators')
        for i in range(self.num_repeats):
            try:
                self.driver.switch_to_window(target)
                self.driver.switch_to_window(0)
                break
            except NoSuchWindowException:
                time.sleep(self.poll)
        else:
            raise NoSuchWindowException("Timed out after %d ms" % timeout)

    
    @seleniumcommand
    def selectWindow(self, target, value):
        """
        Selects a popup window using a window locator. Once a popup window has been selected, all commands go to that window. 
        To select the main window again, use null as the target or leave it empty. The only locator option which is supported currently
        is 'name=' which finds the window using its internal JavaScript "name" property.
        Not yet supported are: 'title' and 'var'. The IDE has sophisticated routine for missing locator option which will most
        likely not be implemented.
        @param target: the JavaScript window ID of the window to select
        @param value:  <not used>
        """
        ttype, ttarget = self._tag_and_value(target)
        if (ttype != 'name' and ttarget != 'null'):
            raise NotImplementedError('only window locators with the prefix "name=" are supported currently')
        if ttarget in ["null", ""]:
            ttarget = 0
        self.driver.switch_to_window(ttarget)

    
    @seleniumcommand
    def selectFrame(self, target, value=None):
        """
        Selects a frame within the current window. (You may invoke this command multiple times to select nested frames.) 
        You can also select a frame by its 0-based index number; select the first frame with "0", or the third frame 
        with "2". To select the top frame, use may use "relative=top". Not yet supported: "relative=parent"
        @param target: an element locator identifying a frame or iframe.
        """
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
     
    def wd_SEL_TextPresent(self, target, value=None):
        """
        Verifies that the specified text pattern appears somewhere on the rendered page shown to the user.
        @param target: a pattern to match with the text of the page 
        @param value: <not used>
        @returns: true if the pattern matches the text, false otherwise
        """
        text = html2text(self.driver.page_source)
        return True, self._isContained(target, text)
   
    def wd_SEL_ElementPresent(self, target, value=None):        
        """
        Verifies that the specified element is somewhere on the page. Catches a NoSuchElementException in order to return a result.
        @param target: an element locator
        @param value: <not used>
        @returns: true if the element is present, false otherwise
        """
        try:
            self._find_target(target)
            return True, True
        except NoSuchElementException:
            return True, False

  
    def wd_SEL_Attribute(self, target, value):
        """
        Gets the value of an element attribute.
        @param target: an element locator followed by an @ sign and then the name of the attribute, e.g. "foo@bar"
        @param value: the expected value of the specified attribute
        @returns: the value of the specified attribute
        """  
        target, sep, attr = target.rpartition("@")
        attrValue = self._find_target(target).get_attribute(attr)
        if attrValue is None:
            raise NoSuchAttributeException
        return value, attrValue.strip()
    
     
    def wd_SEL_Text(self, target, value):
        """
        Gets the text of an element. This works for any element that contains text.
        @param target: an element locator
        @param value: the expected text of the element
        @returns: the text of the element
        """ 
        return value, self._find_target(target).text.strip()
    
    
    def wd_SEL_Value(self, target, value):
        """
        Gets the value of an input field (or anything else with a value parameter).
        @param target: an element locator
        @param value: the expected element value
        @returns: the element value
        """    
        return value, self._find_target(target).get_attribute("value").strip()
    

    def wd_SEL_XpathCount(self, target, value):
        """
        Get the number of nodes that match the specified xpath, eg. "//table" would give the number of tables.
        @param target: an xpath expression to locate an element
        @param value: the number of nodes that should match the specified xpath
        @returns: the number of nodes that match the specified xpath
        """      
        count = len(self.driver.find_elements_by_xpath(target))
        return int(value), count

  
    def wd_SEL_Alert(self, target, value=None):
        """
        Retrieves the message of a JavaScript alert generated during the previous action, or fail if there were no alerts. 
        Getting an alert has the same effect as manually clicking OK. If an alert is generated but you do not consume it 
        with getAlert, the next wedriver action will fail.
        @param target: the expected message of the most recent JavaScript alert
        @param value: <not used>
        @returns: the message of the most recent JavaScript alert
        """
        alert = Alert(self.driver)
        text = alert.text.strip() 
        alert.accept()
        return target, text
    
    
    def wd_SEL_Confirmation(self, target, value=None):
        """
        Webdriver gives no opportunity to distinguish between alerts and confirmations.
        Thus they are handled the same way here, although this does not reflect the exact behavior of the IDE
        """
        return self.wd_SEL_Alert(target, value)
   
  
    def wd_SEL_Table(self, target, value):
        """
        Gets the text from a cell of a table. The cellAddress syntax tableLocator.row.column, where row and column start at 0.
        @param target: a cell address, e.g. "css=#myFirstTable.2.3"
        @param value: the text which is expected in the specified cell.
        @returns: the text from the specified cell
        """ 
        target, row, column = target.rsplit(".", 2)
        table = self._find_target(target)
        pos = "tbody/tr[" + str(int(row) + 1) + "]/*[" +  str(int(column) + 1) + "]"
        return value, table.find_element_by_xpath(pos).text.strip()
     
    ################# Some helper Functions ##################


    def _tag_and_value(self, tvalue):
        # target can be e.g. "css=td.f_transfectionprotocol"
        s = tvalue.split('=', 1)
        tag, value = s if len(s) == 2 else (None, None)
        if not tag in ['xpath', 'css', 'id', 'name', 'link', 'label', 'value', 'index']:
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
        elif ttype == 'xpath':
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
            raise UnexpectedTagNameException('no way to find targets "%s"' % target)
        
        
    def _matches(self, expectedResult, result):
        """
        Try to match result found in HTML with expected result
        @param expectedResult: string containing the 'result' of a selenese command (can be plain text, regex, ...)
        @param result: string obtained from HTML via 'target'
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
        if type(expectedResult) not in [str, unicode]:
            return expectedResult == result
        # 2) regexp
        elif expectedResult.startswith('regexp:'):
            try:
                return result == re.match(expectedResult[7:], result).group(0)
            except AttributeError:
                return False
        # 3) exact-tag:
        elif expectedResult.startswith("exact:"):
            return result == expectedResult[6:]
        # 4) glob/ wildcards
        else:
            if expectedResult.startswith("glob:"):
                expectedResult = expectedResult[5:]
            # using the "fnmatch" module method "fnmatchcase" (aliased to globmatchcase) in order to handle wildcards.
            return globmatchcase(result, expectedResult)
    
    
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
        metacharacters = ['.', '$','|','+','(',')', '[', ']']
        for char in metacharacters:
            wc = wc.replace(char, '\\' + char)
        # translate wildcard characters $ and *
        wc = re.sub(r"(?<!\\)\*", r".*", wc)
        wc = re.sub(r"(?<!\\)\?", r".", wc)
        return wc
    
    
