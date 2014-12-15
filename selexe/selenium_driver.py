import logging
import time
import re
import types
import new
import json
import six
import BeautifulSoup as beautifulsoup

###
from six.moves import xrange

from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchAttributeException
from selenium.common.exceptions import UnexpectedTagNameException
from selenium.common.exceptions import NoSuchFrameException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert


logger = logging.getLogger(__name__)


def create_get_or_is(func, inverse=False):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'is*' or 'get*' function.
    """
    def wrap_func(self, target, value=None):
        expectedResult, result = func(self, target, value=value)
        return result
    return wrap_func


def create_verify(func, inverse=False):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'verify*' function.
    """
    def wrap_func(self, target, value=None):
        try:
            expectedResult, result = func(self, target, value=value)  # can raise NoAlertPresentException
            self._assertMatches(expectedResult, result, inverse)
            return True
        except NoAlertPresentException:
            verificationError = "There were no alerts or confirmations"
        except AssertionError:
            if result == inverse:
                # verifyTextPresent/verifyElementPresent only return True or False, so no proper comparison
                # can be made.
                verificationError = "true" if inverse else "false"
            else:
                verificationError = 'Actual value "%s" did not match "%s"' % (result, expectedResult)
        logger.error(verificationError)
        self.verificationErrors.append(verificationError)        
        return False
    return wrap_func


def create_assert(func, inverse=False):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'assert*' function.
    """
    def wrap_func(self, target, value=None):
        expectedResult, result = func(self, target, value=value)
        self._assertMatches(expectedResult, result,
                            inverse=inverse,
                            message='Actual value "%s" did not match "%s"' % (result, expectedResult))
    return wrap_func


def create_waitFor(func, inverse=False):
    """
    Decorator to convert a test method of class SeleniumCommander (starting with 'wd_SEL*') into a Selenium
    'waitFor*' function.
    """
    def wrap_func(self, target, value=None):
        for i in self.retries:
            try: 
                expectedResult, result = func(self, target, value=value)
                if i == 0:
                    logger.info('... waiting for%s %r' % (' not' if inverse else '', expectedResult))
                self._assertMatches(expectedResult, result, inverse=inverse)
                return
            except (AssertionError, NoAlertPresentException):
                pass
    return wrap_func


def create_store(func, inverse=False):
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
        logger.info('... %s = %r' % (variableName, result))
        self.storedVariables[variableName] = result
    return wrap_func


def create_selenium_methods(cls):
    """
    Class decorator to setup all available wrapping decorators to those methods in class SeleniumCommander
    starting with 'wd_SEL*'
    """
    GENERIC_METHOD_PREFIX = 'wd_SEL_'
    lstr = len(GENERIC_METHOD_PREFIX)

    def decorate_method(cls, methodName, prefix, decoratorFunc, inverse=False, waitDefault=True):
        """
        This method double-decorates a generic webdriver command.
        1. Decorate it with one of the create_get, create_verify... decorators.
           These decorators convert the generic methods into a real selenium commands.
        2. Decorate with the 'seleniumcommand' method decorator.
           This wrapper expands selenium variables in the 'target' and 'value' and
           does the logging.
        """
        seleniumMethodName = prefix + methodName[lstr:]
        func = cls.__dict__[methodName]
        wrappedMethod = decoratorFunc(func, inverse)
        wrappedMethod.wait_for_page = getattr(func, 'wait_for_page', waitDefault)
        wrappedMethod.__name__ = seleniumMethodName
        setattr(cls, seleniumMethodName, seleniumcommand(wrappedMethod))


    for methodName in cls.__dict__.keys():  # must loop over keys() as the dict gets modified while looping
        if methodName.startswith(GENERIC_METHOD_PREFIX):
            prefix = 'is' if methodName.endswith('Present') else 'get'
            decorate_method(cls, methodName, prefix, create_get_or_is)
            decorate_method(cls, methodName, 'verify', create_verify)
            decorate_method(cls, methodName, 'verifyNot', create_verify, inverse=True)
            decorate_method(cls, methodName, 'assert', create_assert)
            decorate_method(cls, methodName, 'assertNot', create_assert, inverse=True)
            decorate_method(cls, methodName, 'waitFor', create_waitFor, waitDefault=False)
            decorate_method(cls, methodName, 'waitForNot', create_waitFor, inverse=True, waitDefault=False)
            decorate_method(cls, methodName, 'store', create_store)
    return cls



def seleniumcommand(method):
    """
    Method decorator for selenium commands in SeleniumCommander class.
    Wraps all available selenium commands for expand selenium variables in 'target' and 'value'
    arguments.
    """
    wait_for_page = getattr(method, 'wait_for_page', True)
    def seleniumMethod(self, target=None, value=None, log=True, **kw):
        if log:
            logger.info('%s(%r, %r)' % (method.__name__, target, value))
        v_target = self._expandVariables(target) if target else target
        v_value  = self._expandVariables(value) if value else value
        # Webdrivers click function is imperfect at now. It it is supposed to wait for a new page to load,
        # but randomly it fails. We use some kind of hack to compensate for this misbehaviour.
        if wait_for_page: # some methods should never wait!!
            self._wait_page_change()
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
    match = re.compile(r"(verifyNot|assertNot|waitForNot)\w+Present").match
    for methodName in cls.__dict__.keys():  # must loop over keys() as the dict gets modified while looping
        if match(methodName):
            method = getattr(cls, methodName)
            def aliasMethod(self, target, value=None):
                return method(self, target, value)
            alias = methodName.replace("Not", "").replace("Present", "NotPresent")
            setattr(cls, alias, aliasMethod)
    # shortcuts
    for shortcutName, methodName in (
        ('store', 'storeExpression'),
        ):
        method = getattr(cls, methodName)
        def aliasMethod(self, target, value=None):
            return method(self, target, value)
        setattr(cls, shortcutName, aliasMethod)
    return cls


####################################################################################################
@create_aliases
@create_selenium_methods
class SeleniumDriver(object):
    _timeout = 1
    _poll = 1
    _num_repeats = 1
    _verification_errors = ()

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """
        Set attributes for commands starting with 'waitFor'. This is done initially.
        Attribute 'wait_for_timeout' specifies the time until a waitFor command will time out in milliseconds.
        """
        self._timeout = timeout
        self._num_repeats = int(timeout / 1000. / self._poll)

    @property
    def poll(self):
        return self._poll

    @poll.setter
    def poll(self, poll):
        """
        Set attributes for commands starting with 'waitFor'. This is done initially.
        Attribute 'poll' specifies the time until the function inside a waitFor command is repeated in seconds.
        """
        self._poll = poll
        self._num_repeats = int(self._timeout / 1000. / poll)

    @property
    def retries(self):
        """
        Iterable that sleeps and raises RuntimeError timeout if exhausted
        """
        for i in xrange(self._num_repeats):
            yield
            time.sleep(self._poll)
        raise RuntimeError("Timed out after %d ms" % self._timeout)

    @property
    def verification_errors(self):
        return list(self._verification_errors)


    def __init__(self, driver, base_url, timeout=10000, poll=0.1):
        self.driver = driver
        self.base_url = base_url or ''
        self._verification_errors = []
        self._importUserFunctions() # FIXME
        self.timeout = timeout
        self.poll = poll
        # 'storedVariables' is used through the 'create_store' decorator above to store values during a selenium run:
        self.storedVariables = {}
        # Sometimes it is necessary to confirm that a page has actually loaded. We use this variable for it.
        # Take a look at seleniumMethod(), assertPageLoad() and self.clickAndWait().
        self.waitForPageId = False

    def clean_verification_errors(self):
        """
        Clean verification errors
        """
        del self.verification_errors[:]

    def __call__(self, command, target, value=None, **kw):
        """
        Make an actual call to a Selenium action method.
        Examples for methods are 'verifyText', 'assertText', 'waitForText', etc., so methods that are
        typically available in the Selenium IDE.
        Most methods are dynamically created through decorator functions (from 'wd_SEL*-methods) and hence are
        dynamically looked up in the class dictionary.
        """
        try:
            method = getattr(self, command)
        except AttributeError:
            raise NotImplementedError('no proper function for sel command "%s" implemented' % command)
        return method(target, value, **kw)

    def _importUserFunctions(self):
        """
        Import user functions from module userfunctions. 
        Each function in module userfunction (excluding the ones starting with "_") has to take 
        3 arguments: SeleniumDriver instance, target string, value string. Wrap these function 
        by the decorator function "seleniumcommand" and add them as bound methods. 
        """
        try:
            import userfunctions
            funcNames = [key for (key, value) in userfunctions.__dict__.iteritems() \
                         if isinstance(value, types.FunctionType) and not key.startswith("_")]
            for funcName in funcNames:
                newBoundMethod = new.instancemethod(seleniumcommand(getattr(userfunctions, funcName)), self, SeleniumDriver)
                setattr(self, funcName, newBoundMethod)
            logger.info("User functions: " + ", ".join(funcNames))
        except ImportError:
            logger.info("Using no user functions")

    def _expect_page_change(self):
        """
        Save current document id for detecting later page changes by methods should wait for them.
        """
        try:
            self.waitForPageId = self._find_target('css=html')._id
        except:
            pass

    def _wait_page_change(self):
        """
        Wait until document id changes (using `waitForPageId` set by `_expect_page_change`)
        """
        if self.waitForPageId is None:
            return
        logger.info('... waiting for pageload')
        for i in self.retries:
            try:
                newPageId = self._find_target('css=html')._id
                if self.waitForPageId != newPageId:
                    self.waitForPageId = None
                    break
            except (WebDriverException, NoSuchElementException):
                pass

    sel_var_pat = re.compile(r'\${([\w\d]+)}')
    def _expandVariables(self, s):
        """
        Expand variables contained in selenese files.
        Multiple variables can be contained in a string from a selenese file. The format is ${<VARIABLENAME}.
        Those are replaced from self.storedVariables via a re.sub() method.
        """
        return self.sel_var_pat.sub(lambda matchobj: self.storedVariables[matchobj.group(1)], s)

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

    ########################################################################################################
    # The actual translations from selenium-to-webdriver commands

    ###
    # Section 1: Interactions with the browser
    ###

    @seleniumcommand
    def open(self, target, value=None):
        """
        Open a URL in the browser and wait until the browser receives a new page
        @param target: URL (string)
        @param value: <not used>
        """
        self._expect_page_change()
        if not '://' in target:
            target = '%s%s' % (self.base_url, target)
        self.driver.get(target)

    @seleniumcommand
    def clickAndWait(self, target, value=None):
        """
        Click onto a HTML target (e.g. a button) and wait until the browser receives a new page
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        self._expect_page_change()
        self._find_target(target).click()
        
    @seleniumcommand
    def click(self, target, value=None):
        """
        Click onto a HTML target (e.g. a button)
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        for i in self.retries:
            try:
                self._find_target(target).click()
                break
            except NoSuchElementException:
                continue
    
    
    @seleniumcommand
    def select(self, target, value):
        """
        Select an option of a select box.
        @param target: a element locator pointing at a select element
        @param value: an option locator which points at an option of the select element
        Option locators can have the following formats:
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
        # the select command in the IDE does not execute javascript. So skip this command if javascript is executed
        # and wait for the following click command to execute the click event which will lead you to the next page
        if not target_elem.find_elements_by_css_selector('option[onclick]'):
            #import pdb; pdb.set_trace()
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
                raise UnexpectedTagNameException("Unknown option locator tag: " + tag)

    @seleniumcommand
    def waitForPageToLoad(self, target=None, tvalue=None):
        """
        Wait until page changes
        @param target: <not used>
        @param tvalue: <not used>
        """
        self._wait_page_load() # wait code is in another method avoiding recursion
        
    @seleniumcommand
    def type(self, target, value):
        """
        Type text into an input element.
        @param target: an element locator
        @param value: the text to type
        """
        target_elem = self._find_target(target)
        target_elem.clear()
        target_elem.send_keys(value)
        
  
    @seleniumcommand
    def check(self, target, value=None):
        """
        Check a toggle-button (checkbox/radio).
        @param target: an element locator
        @param value: <not used>
        """
        target_elem = self._find_target(target)
        if not target_elem.is_selected():
            target_elem.click()

    @seleniumcommand
    def uncheck(self, target, value=None): 
        """
        Uncheck a toggle-button (checkbox/radio).
        @param target: an element locator
        @param value: <not used>
        """
        target_elem = self._find_target(target)
        if target_elem.is_selected():
            target_elem.click()


    @seleniumcommand
    def mouseOver(self, target, value=None):
        """
        Simulate a user moving the mouse over a specified element.
        @param target: an element locator
        @param value: <not used>
        """
        target_elem = self._find_target(target)
        # Action Chains will not work with several Firefox Versions. Firefox Version 10.2 should be ok.
        ActionChains(self.driver).move_to_element(target_elem).perform()

  
    @seleniumcommand
    def fireEvent(self, target, value):
        """
        """
        if (value == 'blur'):
            target_elem = self._find_target(target)
            actions = ActionChains(self.driver)
            actions.move_to_element(target_elem)
            actions.move_by_offset(target_elem.size["width"] / 2 + 1, 0)
            actions.click().perform()
        
  
    @seleniumcommand
    def mouseOut(self, target, value=None):
        """
        Simulate a user moving the mouse away from a specified element.
        @param target: an element locator
        @param value: <not used>
        """
        target_elem = self._find_target(target)
        actions = ActionChains(self.driver)
        actions.move_to_element(target_elem)
        actions.move_by_offset(target_elem.size["width"] / 2 + 1, 0).perform()
        

    @seleniumcommand
    def waitForPopUp(self, target, value):
        """
        Wait for a popup window to appear and load up.
        @param target: the JavaScript window "name" of the window that will appear (not the text of the title bar).
        @param value: the timeout in milliseconds, after which the function will raise an error. If this value
        is not specified, the default timeout will be used. See the setTimeoutAndPoll function for the default timeout.
        """
        locator = 'null' if target == 'null' else 'name=%s' % target
        for i in self.retries:
            try:
                self._selectWindow(locator)
                self.driver.switch_to_window(0)
                self._find_target('css=html')._id
                break
            except (NoSuchWindowException, WebDriverException):
                pass


    @seleniumcommand
    def selectWindow(self, target, value=None):
        """
        Select a popup window using a window locator. Once a popup window has been selected, all commands go to that window. 
        To select the main window again, use null as the target or leave it empty. The only locator option which is supported currently
        is 'name=' which finds the window using its internal JavaScript "name" property.
        Not yet supported are: 'title' and 'var'. The IDE has sophisticated routine for missing locator option which will most
        likely not be implemented.
        @param target: the JavaScript window ID of the window to select
        @param value: <not used>
        """
        self._selectWindow(target)
    
    
    def _selectWindow(self, target):
        ttype, ttarget = self._tag_and_value(target)
        if ttarget in ('null', '', None):
            self.driver.switch_to_window(0)
        elif ttarget == '_blank':
            self.driver.switch_to_window(self.driver.window_handles[1])
        elif ttype == 'name':
            self.driver.switch_to_window(ttarget)
        elif ttype == 'title':
            for window in self.driver.window_handles:
                self.driver.switch_to_window(window)
                if self.driver.find_element_by_xpath("//title").text == ttarget:
                    break
        else:
            raise NotImplementedError('No way to find the window: use "name" or "title" locators of specify target as "null"')
        
    @seleniumcommand    
    def selectPopUp(self, target, value=None):
        """
        Alias for selectWindow.
        """
        self.selectWindow(target, value)
    
    @seleniumcommand
    def selectFrame(self, target, value=None):
        """
        Select a frame within the current window. (You may invoke this command multiple times to select nested frames.) 
        You can also select a frame by its 0-based index number; select the first frame with "0", or the third frame 
        with "2". To select the top frame, you may use "relative=top". Not yet supported is "relative=parent".
        @param target: an element locator identifying a frame or iframe.
        @param value: <not used>
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
        Verify that the specified text pattern appears somewhere on the page shown to the user.
        @param target: a pattern to match with the text of the page 
        @param value: <not used>
        @return: true if the pattern matches the text, false otherwise
        """
        text = beautifulsoup.BeautifulSoup(self.driver.page_source).text
        return True, self._isContained(target, text)
    
   
    def wd_SEL_Location(self, target, value=None):
        """
        Get absolute url of current page
        @param target:
        @param value: <not used>
        """
        return target, self.driver.current_url


    def wd_SEL_Visible(self, target, value=None):
        """
        Get if element for given locator is visible
        @param target:
        @param value: <not used>
        """
        try:
            return True, self._find_target(target).is_displayed()
        except NoSuchElementException:
            return True, False


    def wd_SEL_ElementPresent(self, target, value=None):        
        """
        Verify that the specified element is somewhere on the page. Catch a NoSuchElementException in order to return a result.
        @param target: an element locator
        @param value: <not used>
        @return: true if the element is present, false otherwise
        """
        try:
            self._find_target(target)
            return True, True
        except NoSuchElementException:
            return True, False

  
    def wd_SEL_Attribute(self, target, value):
        """
        Get the value of an element attribute.
        @param target: an element locator followed by an @ sign and then the name of the attribute, e.g. "foo@bar"
        @param value: the expected value of the specified attribute
        @return: the value of the specified attribute
        """  
        target, sep, attr = target.rpartition("@")
        attrValue = self._find_target(target).get_attribute(attr)
        if attrValue is None:
            raise NoSuchAttributeException
        return value, attrValue.strip()


    def wd_SEL_Expression(self, target, value):
        """
        Get given expression value
        @param target: value to store
        @param value: variable name
        @return: the value of the specified attribute
        """
        return value, target


    def wd_SEL_Eval(self, target, value):
        """
        Get value returned by given javascript expression
        @param target: value to store
        @param value: variable name
        @return: the value of the specified attribute
        """
        reset = ['document'] # ensure consistent behavior
        js = (
            'var %s,'
                'storedVars = %s,'
                'r = eval(\'%s\');'
            'return [\'\'+(r===undefined?null:r), storedVars];'
        ) % (
            ',    '.join('%s = undefined' % i for i in reset),
            json.dumps(self.storedVariables),
            target.replace('\'', '\\\''),
        )
        result, self.storedVariables = self.driver.execute_script(js)
        return value, result
    
     
    def wd_SEL_Text(self, target, value):
        """
        Get the text of an element. This works for any element that contains text.
        @param target: an element locator
        @param value: the expected text of the element
        @return: the text of the element
        """
        return value, self._find_target(target).text.strip()
    
    
    def wd_SEL_Value(self, target, value):
        """
        Get the value of an input field (or anything else with a value parameter).
        @param target: an element locator
        @param value: the expected element value
        @return: the element value
        """    
        return value, self._find_target(target).get_attribute("value").strip()
    

    def wd_SEL_XpathCount(self, target, value):
        """
        Get the number of nodes that match the specified xpath, e.g. "//table" would give the number of tables.
        @param target: an xpath expression to locate elements
        @param value: the number of nodes that should match the specified xpath
        @return: the number of nodes that match the specified xpath
        """      
        count = len(self.driver.find_elements_by_xpath(target))
        return int(value), count

  
    def wd_SEL_Alert(self, target, value=None):
        """
        Retrieve the message of a JavaScript alert generated during the previous action, or fail if there are no alerts. 
        Getting an alert has the same effect as manually clicking OK. If an alert is generated but you do not consume it 
        with getAlert, the next webdriver action will fail.
        @param target: the expected message of the most recent JavaScript alert
        @param value: <not used>
        @return: the message of the most recent JavaScript alert
        """
        alert = Alert(self.driver)
        text = alert.text.strip()
        alert.accept()
        return target, text
    wd_SEL_Alert.wait_for_page = False
    
    
    def wd_SEL_Confirmation(self, target, value=None):
        """
        Webdriver gives no opportunity to distinguish between alerts and confirmations.
        Thus they are handled the same way here, although this does not reflect the exact behavior of the IDE
        """
        return self.wd_SEL_Alert(target, value)
    wd_SEL_Confirmation.wait_for_page = False
   
  
    def wd_SEL_Table(self, target, value):
        """
        Get the text from a cell of a table. The cellAddress syntax is tableLocator.row.column, where row and column start at 0.
        @param target: a cell address, e.g. "css=#myFirstTable.2.3"
        @param value: the text which is expected in the specified cell.
        @return: the text from the specified cell
        """ 
        target, row, column = target.rsplit(".", 2)
        table = self._find_target(target)
        rows = []
        # collect all rows  from the possible table elements in the needed order
        for tableElem in ['thead', 'tbody', 'tfoot']:    
            rows.extend(table.find_elements_by_xpath(tableElem + '/*'))
        # get the addressed child element of the addressed row    
        cell = rows[int(row)].find_elements_by_xpath('*')[int(column)]
        return value, cell.text.strip()

    ################# Some helper Functions ##################

    @classmethod
    def _tag_and_value(cls, target):
        """
        Get the tag of an element locator to identify its type.
        @param target: an element locator
        @return: an element locator splited into its tag and value.

        Examples:

        >>> SeleniumDriver._tag_and_value('css=td.f_transfectionprotocol')
        ('css', 'td.f_transfectionprotocol')
        >>> SeleniumDriver._tag_and_value("xpath=//td[@id='f_transfectionprotocol']")
        ('xpath', "//td[@id='f_transfectionprotocol']")
        >>> SeleniumDriver._tag_and_value("//td[@id='f_transfectionprotocol']")
        ('xpath', "//td[@id='f_transfectionprotocol']")
        >>> SeleniumDriver._tag_and_value('f_transfectionprotocol')
        (None, 'f_transfectionprotocol')
        >>> SeleniumDriver._tag_and_value('id=f_transfectionprotocol')
        ('id', 'f_transfectionprotocol')
        """
        if target.startswith('/'):
            # Identify an xpath locator missing a tag by looking at the leading tokens.
            # This separate handling saves this locator variant from a split operation which may cut it in two
            # worthless pieces (example 3).
            return ('xpath', target)
        elif '=' in  target:
            # Perform a split for all other locator types to get the tag. If there is no tag, specify it as None.
            return target.split('=', 1) # Unknown tags raise an UnexpectedTagNameException in further processing
        # Older IDE Versions did not specify an "id" or "name" tag while recording (example 4).
        # We support these non-tag locators because the IDE still does. The ambiguity is easily handled in further
        # processing.
        return ('xpath', '//[@id=\'%s\' or @name=\'%s\']' % (target, target))

    def _find_target(self, target):
        """
        Select and execute the appropriate find_element_* method for an element locator.
        @param target: an element locator
        @return: the webelement instance found by a find_element_* method
        """
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
            # `find_element_by_link_text` exposes a different behavior than Selenium IDE applying css transformations
            # so we cannot use `find_element_by_partial_link_text` nor `find_element_by_link_text` methods
            # Bug report: https://code.google.com/p/selenium/issues/detail?id=6950
            return self.driver.find_element_by_xpath('//a[text()=\'%s\']' % ttarget)
        else:
            raise UnexpectedTagNameException('no way to find targets "%s"' % target)

    @classmethod
    def _matches(cls, expectedResult, result):
        """
        Try to match a result of a selenese command with its expected result.
        The function performs a plain equality comparison for non-Strings and handles all three kinds of String-match patterns which Selenium defines:
        1) plain equality comparison
        2) exact: a non-wildcard expression
        3) regexp: a regular expression
        4) glob: a (possible) wildcard expression. This is the default (fallback) method if 1), 2) and 3) don't apply
        see: http://release.seleniumhq.org/selenium-remote-control/0.9.2/doc/dotnet/Selenium.html    
        @param expectedResult: the expected result of a selenese command
        @param result: the actual result of a selenese command
        @return: true if matches, false otherwise
        """
        # 1) equality expression (works for booleans, integers, etc)
        if not isinstance(expectedResult, six.string_types):
            return expectedResult == result
        # 2) exact-tag:
        elif expectedResult.startswith("exact:"):
            return result == expectedResult[6:]
        # 3) regexp
        elif expectedResult.startswith('regexp:'):
            expectedResult = expectedResult[7:]
        # 4) glob/ wildcards
        else:
            if expectedResult.startswith("glob:"):
                expectedResult = expectedResult[5:]
            expectedResult = cls._translateWilcardToRegex(expectedResult)
        match = re.match(expectedResult, result)
        return match and result == match.group(0)

    @classmethod
    def _assertMatches(cls, expectedResult, result, inverse=False, message=None):
        """

        @param expectedResult:
        @param result:
        @param inverse:
        """
        matches = cls._matches(expectedResult, result)
        if inverse:
            matches = not matches
        assert (matches, message) if message else matches

    @classmethod
    def _isContained(cls, pat, text):
        """
        Verify that a string pattern can be found somewhere in a text.
        This function handles all three kinds of String-match Patterns which Selenium defines. See the _matches method for further details.
        @param pat: a string pattern
        @param text: a text in which the pattern should be found
        @return: true if found, false otherwise
        """
        # strings of each pattern may end with "..." to shorten them.
        pat = cls._sel_pattern_abbreviation(pat)
        # 1) regexp
        if pat.startswith('regexp:'):
            return re.search(pat[7:], text) is not None
        # 2) exact-tag:
        elif pat.startswith("exact:"):
            return pat[6:] in text
        # 3) glob/ wildcards
        if pat.startswith("glob:"):
            pat = pat[5:]
        pat = cls._translateWilcardToRegex(pat)
        return re.search(pat, text) is not None
    

    @classmethod
    def _sel_pattern_abbreviation(cls, aString):
        if aString.endswith("..."): 
            aString = aString.replace("...", ".*")
        return aString
        

    @classmethod
    def _translateWilcardToRegex(cls, wc):
        """
        Translate a wildcard pattern into in regular expression (in order to search with it in Python).
        Note: Since the IDE wildcard expressions do not support bracket expressions they are not handled here.
        @param wc: a wildcard pattern
        @return: the translation into a regular expression.
        """
        # escape metacharacters not used in wildcards
        metacharacters = ['.', '$','|','+','(',')', '[', ']']
        for char in metacharacters:
            wc = wc.replace(char, '\\' + char)
        # translate wildcard characters $ and *
        wc = re.sub(r"(?<!\\)\*", r".*", wc)
        wc = re.sub(r"(?<!\\)\?", r".", wc)
        return wc
