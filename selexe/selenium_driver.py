"""
Selenium driver module

Selexe's selenium driver provides Selenium core API methods in top of webdriver API, using Selenium IDE implementation
as reference.

"""
import itertools
import logging
import time
import re
import math
import new
import json
import six
import functools
import bs4 as beautifulsoup
import selenium.webdriver

from six.moves import xrange

from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException, NoSuchAttributeException, \
    UnexpectedTagNameException, NoSuchFrameException, WebDriverException, TimeoutException, InvalidSelectorException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert

from selenium_command import seleniumcommand, seleniumimperative, seleniumgeneric, selenium_multicommand_discover, \
    NOT_PRESENT_EXCEPTIONS
from selenium_external import ExternalElement, ExternalContext, element_context, original_element

logger = logging.getLogger(__name__)


class SeleniumDriver(object):
    __metaclass__ = selenium_multicommand_discover

    _timeout = 1
    _poll = 1
    _num_retries = 1
    _verification_errors = ()
    _by_target_locators = {
        'css': By.CSS_SELECTOR,
        'id': By.ID,
        'name': By.NAME,
        'xpath': By.XPATH,
    }
    _target_locators = {
        'identifier': lambda t, v:
        ('xpath', v) if v.startswith('//') else
        ('dom', v) if v.startswith('document.') else
        ('xpath', '//*[@id=\'%s\' or @name=\'%s\']' % (v, v)),
        'id': None,
        'name': None,
        'dom': None,
        'xpath': None,
        'link': ('xpath', '//a[normalize-space(text())=\'%(value)s\']'),
        'css': None,
        'ui': None,
    }
    sleep = staticmethod(time.sleep)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """
        Time until a waitFor command will time out in milliseconds.
        """
        self._timeout = int(timeout)
        self._num_retries = self._count_retries()

        # self.driver.set_page_load_timeout(timeout) # not sure about this should or shouldn't be set
        self.driver.set_script_timeout(timeout)

    @property
    def poll(self):
        return self._poll

    @poll.setter
    def poll(self, poll):
        """
        Time until the function inside a waitFor command is repeated in milliseconds.
        """
        self._poll = int(poll)
        self._num_retries = self._count_retries()

    def _deprecate_page(self):
        self.driver.execute_script('document._deprecated_by_selexe=true;')

    def _wait_pageload(self, timeout=None):
        """
        Waits for document to get loaded. If document has frames, wait for them too.
        """
        script = 'return (document.readyState===\'complete\')&&(!document._deprecated_by_selexe);'
        for retry in self._retries(timeout=timeout):
            if self.driver.execute_script(script):
                break

    def _count_retries(self, timeout=None, poll=None):
        """
        Get number of retries for given timeout and polling time.
        @param timeout: minimum timeout should be waited, defaults to current timeout
        @param poll: time between retries, defaults to current polling time
        @return: number of retries
        """
        if timeout is None:
            timeout = self._timeout
        if poll is None:
            poll = self._poll
        return int(math.ceil(float(timeout) / poll))

    def _retries(self, timeout=None):
        """
        Iterable that sleeps, poll and finally raises RuntimeError timeout if exhausted

        @param timeout: timeout in milliseconds, defaults to default timeout
        @yields None before sleeping continuously until timeout
        @raises TimeoutException if timeout is exhausted
        """
        repeats = self._num_retries if timeout is None else self._count_retries(timeout=timeout)
        poll = self._poll / 1000.
        for i in xrange(repeats):
            yield i
            self.sleep(poll)
        raise TimeoutException("Timed out after %d ms" % (self._timeout if timeout is None else timeout))

    def _autotimeout(self, timeout=None):
        """
        Iterable that iterate until timeout gets exhausted. It's less efficient than _retries, but more accurate.

        @param timeout: timeout in milliseconds, defaults to default timeout
        @yields remaining timeout
        @raises TimeoutException if timeout is exhausted
        """
        timeout = self._timeout if timeout is None else timeout
        dest = time.time() + timeout/1000.
        poll = self._poll / 1000.
        ct = time.time()
        while ct < dest:
            yield int((dest-ct)*1000)
            nt = time.time()
            if nt-ct < poll:
                self.sleep(poll-nt+ct)
                ct += poll
            else:
                ct = nt
        raise TimeoutException("Timed out after %d ms" % timeout)

    @property
    def verification_errors(self):
        """
        List of verification errors

        :return: safe copy if internal verification error list
        """
        return list(self._verification_errors)

    def __init__(self, driver, baseuri=None, timeout=30000, poll=100):
        """
        @param driver: selenium WebDriver instance

        @param baseuri: base url or None
        @param timeout: timeout in milliseconds
        @param poll: polling interval in milliseconds
        """

        self.driver = driver
        """
        @type : selenium.webdriver.Remote
        """
        self.baseuri = baseuri or ''
        self._verification_errors = []
        self._importUserFunctions()  # FIXME
        self.timeout = timeout
        self.poll = poll
        self.custom_locators = {}
        # 'storedVariables' is used through the 'create_store' decorator above to store values during a selenium run:
        self.storedVariables = {}

    def clean_verification_errors(self):
        """
        Clean verification errors
        """
        del self._verification_errors[:]

    def save_screenshot(self, path):
        """
        Save screenshot to given file path.

        @param path: filename where screenshot will be written on.
        """
        self.driver.save_screenshot(path)

    def __call__(self, command, target=None, value=None, **kw):
        """
        Make an actual call to a Selenium action method.

        Examples for methods are 'verifyText', 'assertText', 'waitForText', etc., so methods that are
        typically available in the Selenium IDE.

        Most methods are dynamically created through decorator functions (from 'wd_SEL*-methods) and hence are
        dynamically looked up in the class dictionary.

        @param command: Selenium IDE command.
        @param target: command's first parameter, usually target.
        @param value: command's second parameter, optional.
        @param **kw: commamnd's extra keyword arguments, optional.
        @return value returned by command, usually True, False or string.
        """
        try:
            method = getattr(self, command)
        except AttributeError:
            raise NotImplementedError('no proper function for sel command "%s" implemented' % command)
        return method(target, value, **kw)

    def _importUserFunctions(self):  # TODO: replace for flexibility
        """
        Import user functions from module userfunctions. 
        Each function in module userfunction (excluding the ones starting with "_") has to take 
        3 arguments: SeleniumDriver instance, target string, value string. Wrap these function 
        by the decorator function "seleniumcommand" and add them as bound methods. 
        """
        try:
            import userfunctions

            fncdict = {key: value for key, value in six.iteritems(userfunctions.__dict__)
                       if not key.startswith("_") and callable(value)}
            for funcName, fnc in six.iteritems(fncdict):
                newBoundMethod = new.instancemethod(seleniumcommand(fnc), self, SeleniumDriver)
                setattr(self, funcName, newBoundMethod)
            logger.info("User functions: %s" % ", ".join(fncdict))
        except ImportError:
            logger.info("Using no user functions")

    def _expandVariablesCallback(self, match):
        return self.storedVariables.get(match.group(1), match.group(0))

    _sel_var_pat = re.compile(r'\${([\w\d]+)}')

    def _expandVariables(self, s):
        """
        Expand variables contained in selenese files.
        Multiple variables can be contained in a string from a selenese file. The format is ${<VARIABLENAME}.
        Those are replaced from self.storedVariables via a re.sub() method.

        @param s: text whose variables will be expanded
        @return given text with expanded variables
        """
        return self._sel_var_pat.sub(self._expandVariablesCallback, s)

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

    def _writeScript(self, content, id=None, where='head'):
        """
        Writes given script into an script element similarly to runScript.

        :param content: script content
        :param id: script tag id
        :param where: where script should be placed (head or body)
        """
        set_id_part = 'script.attributes.id=\'%s(id)s\';' if id else ''
        script = (
                     'var parent=document.getElementsByTagName(\'%(parent)s\')[0]||document,'
                     'script=document.createElement(\'script\'),'
                     'content=document.createTextNode(%(content)s);'
                     'script.attributes.type=\'text/javascript\';'
                     '%(set_id_part)s'
                     'script.appendChild(content);'
                     'parent.appendChild(script);'
                 ) % {
                     'parent': where,
                     'set_id_part': set_id_part,
                     'content': json.dumps(content),
                 }
        self.driver.execute_script(script)

    @seleniumcommand.nowait  # 'open' has no AndWait variant
    def open(self, target, value=None):
        """
        Open a URL in the browser and wait until the browser receives a new page
        @param target: URL (string)
        @param value: <not used>
        """
        if not '://' in target:
            if not self.baseuri:
                raise RuntimeError('Relative %r cannot be resolved, baseuri not specified.' % target)
            if target[0] == '/':
                target = '%s%s' % (self.baseuri, target)
            else:
                target = '%s/%s' % (self.driver.current_url.rstrip('/'), target.lstrip('/'))
        self._deprecate_page()
        self.driver.get(target)
        self._wait_pageload()

    @seleniumimperative.nowait
    def refresh(self, target=None, value=None):
        """
        Simulates the user clicking the "Refresh" button on their browser.
        """
        # NOTE: this used to be done by seleniumcommand, but can be loaded with the same url so we need this
        self._deprecate_page()
        self.driver.refresh()
        self._wait_pageload()

    @seleniumimperative
    def click(self, target, value=None):
        """
        Click onto a HTML target (e.g. a button)
        @param target: a string determining an element in the HTML page
        @param value:  <not used>
        """
        for retry in self._retries():
            try:
                target = self._find_target(target, click=True)
                self._event(target, 'click')
                break
            except NOT_PRESENT_EXCEPTIONS:
                continue

    @seleniumimperative
    def windowFocus(self, target, value=None):
        """
        Gives focus to the currently selected window
        """
        self.driver.execute_script('window.focus();')

    @seleniumimperative
    def windowMaximize(self, target, value=None):
        """
        Resize currently selected window to take up the entire screen
        """
        self.driver.maximize_window()

    @seleniumcommand
    def select(self, target, value):
        """
        Select an option from a drop-down using an option locator.

        Option locators provide different ways of specifying options of an HTML Select element (e.g. for selecting a
        specific option, or for asserting that the selected option satisfies a specification). There are several forms
        of Select Option Locator.

        @param target: an element locator identifying a drop-down menu
        @param value: an option locator (a label by default) which points at an option of the select element

        Option locator format
        ----------------------

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
        tag, tvalue = self._tag_and_value(value, locators=('id', 'label', 'value', 'index'), default='label')
        select = Select(target_elem)
        # the select command in the IDE does not execute javascript. So skip this command if javascript is executed
        # and wait for the following click command to execute the click event which will lead you to the next page
        if not target_elem.find_elements_by_css_selector('option[onclick]'):
            if tag == 'label':
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

    @seleniumcommand
    def close(self, target=None, value=None):
        """
        Simulates the user clicking the "close" button in the titlebar of a popup window or tab.

        :return:
        """
        self.driver.close()

    @seleniumcommand
    def waitForPageToLoad(self, target=None, value=None):
        """
        Wait until page changes
        """
        self._wait_pageload()

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
    def check(self, target, value):
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

    def _event(self, target, name):
        """
        Generate given event with webdriver

        @param target: target element or locator
        @param name: event name
        """
        element = self._find_target(target) if isinstance(target, six.string_types) else target
        with element_context(element):
            if name == 'blur':
                self._event(element, 'focus')
                body = self._find_target('css=body')
                chain = ActionChains(self.driver)
                chain.move_to_element(body)
                chain.click(body)
                chain.perform()
            elif name == 'focus':
                if element.tag_name == 'input':
                    element.send_keys('')
                else:
                    chain = ActionChains(self.driver)
                    chain.move_to_element(element)
                    chain.perform()
            elif name == 'mouseover':
                chain = ActionChains(self.driver)
                chain.move_to_element(element)
                chain.perform()
            elif name == 'mouseout':
                body = self._find_target('css=body')
                chain = ActionChains(self.driver)
                chain.move_to_element(element)
                chain.perform()
                chain.move_to_element_with_offset(body, -1, -1)
                chain.perform()
            elif name == 'click':
                chain = ActionChains(self.driver)
                chain.move_to_element(element)
                chain.click(element)
                chain.perform()
            else:
                logger.exception('Event trigger for %r is not implemented yet, will be ignored.' % name)


    @seleniumimperative
    def mouseOver(self, target, value=None):
        """
        Simulate a user moving the mouse over a specified element.
        @param target: an element locator
        @param value: <not used>
        """
        self._event(target, 'mouseover')

    @seleniumcommand
    def fireEvent(self, target, value):
        """
        @param target: an element locator
        @param value: <not used>
        """
        self._event(target, value)

    @seleniumimperative
    def mouseOut(self, target, value=None):
        """
        Simulate a user moving the mouse away from a specified element.
        @param target: an element locator
        @param value: <not used>
        """
        self._event(target, 'mouseout')

    @seleniumcommand.nowait
    def waitForPopUp(self, target=None, value=None):
        """
        Wait for a popup window to appear and load up.
        @param target: the JavaScript window "name" of the window that will appear (not the text of the title bar). If unspecified, or specified as 'null', this command will wait for the first non-top window to appear (don't rely on this if you are working with multiple popups simultaneously).
        @param value: a timeout in milliseconds, after which the action will return with an error. If this value is not specified, the default Selenium timeout will be used. See the setTimeout() command.
        """
        timeout = None if value in (None, '', 'null') else int(value)
        if target in (None, '', 'null'):
            one = False
            for timeout in self._autotimeout(timeout):
                for handle in self.driver.window_handles:
                    with ExternalContext(self.driver, window_handle=handle):
                        if self._window_is_popup():
                            self._wait_pageload(timeout)
                            one = True
                if one:
                    break
        else:
            current_window_handle = self.driver.current_window_handle
            for timeout in self._autotimeout(timeout):
                try:
                    self._selectWindow(target, mode='popup')
                    self._wait_pageload(timeout)
                    break
                except NoSuchWindowException:
                    continue
                finally:
                    self.driver.switch_to.window(current_window_handle)


    @seleniumcommand
    def setTimeout(self, target, value=None):
        """
        Specifies the amount of time that Selenium will wait for actions to complete.

        Actions that require waiting include "open" and the "waitFor*" actions.
        The default timeout is 30 seconds.

        @param target: a timeout in milliseconds, after which the action will return with an error
        """
        self.timeout = int(target)

    @seleniumimperative
    def setSpeed(self, target, value=None):
        """
        Set execution speed (i.e., set the millisecond length of a delay which will follow each selenium operation).
        By default, there is no such delay, i.e., the delay is 0 milliseconds.

        @param target:  the number of milliseconds to pause after operation
        """
        self.driver.implicitly_wait(int(target) / 1000.)

    @seleniumimperative
    def deleteCookie(self, target=None, value=None):
        """
        Delete a named cookie with specified path and domain.

        Be careful; to delete a cookie, you need to delete it using the exact same path and domain that were used to create the cookie. If the path is wrong, or the domain is wrong, the cookie simply won't be deleted.

        Also note that specifying a domain that isn't a subset of the current domain will usually fail.

        Since there's no way to discover at runtime the original path and domain of a given cookie, we've added an option called 'recurse' to try all sub-domains of the current domain with all paths that are a subset of the current path. Beware; this option can be slow. In big-O notation, it operates in O(n*m) time, where n is the number of dots in the domain name and m is the number of slashes in the path.

        @param target:  the name of the cookie to be deleted
        @param value:  options for the cookie. Currently supported options include 'path', 'domain' and 'recurse.' The optionsString's format is "path=/path/, domain=.foo.com, recurse=true". The order of options are irrelevant. Note that specifying a domain that isn't a subset of the current domain will usually fail.
        """
        path = None
        domain = None
        recurse = None
        if value:
            if value.startswith('path='):
                path = value[5:]
            elif value.startswith('domain='):
                domain = value[7:]
            elif value.startswith('recurse='):
                recurse = True if value[8:] == 'true' else False

        # TODO: check if this behavior is correct
        cookies = self.driver.get_cookies() if target in (None, 'null', '', '*') else self.driver.get_cookies()(
            self.driver.get_cookie(target), )
        for cookie in cookies:
            samepath = True
            if path:
                samepath = cookie.get('path', None) == path
            samedomain = True
            if domain:
                samedomain = cookie['domain'].endswith(domain) if recurse and 'domain' in cookie else (
                cookie.get('domain', None) == domain)
            if samepath and samedomain:
                self.driver.delete_cookie(target)

    @seleniumimperative
    def deleteAllVisibleCookies(self, target=None, value=None):
        """
        Calls deleteCookie with recurse=true on all cookies visible to the current page.
        """
        self.driver.delete_all_cookies()

    def _selectWindowByName(self, name):
        """
        Switch to window with given window name

        @param name: str
        @return: handle of the window
        @raises: NoSuchWindowException if not found
        """
        try:
            self.driver.switch_to.window(name)
        except NoSuchWindowException:
            raise NoSuchWindowException('Could not find window with name %s' % name)

    def _selectWindowByTitle(self, title):
        """
        Switch to window with given title

        @param title: str
        @return: handle of the window
        @raises: NoSuchWindowException if not found
        """
        current_window_handle = self.driver.current_window_handle
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            try:
                if self.driver.find_element_by_xpath("/html/head/title").text == title:
                    return
            except NoSuchElementException:
                pass
        self.driver.switch_to.window(current_window_handle)
        raise NoSuchWindowException('Could not find window with title %s' % title)

    def _selectWindowByExpression(self, expression):
        """
        Switch to window with given javascript expression

        @param title: str
        @return: handle of the window
        @raises: NoSuchWindowException if not found
        """
        current_window_handle = self.driver.current_window_handle
        attribute = '_selexe_window_selected_from'
        json_handle = json.dumps(current_window_handle)
        # Mark window as requested by current window
        script = (
            'var w = eval(%(code)s);'
            'return w&&!!(w.%(attribute)s=%(handle)s);'
            ) % {
            'code': json.dumps(expression),
            'attribute': attribute,
            'handle': json_handle,
            }
        try:
            found = self.driver.execute_script(script)
        except WebDriverException:
            raise NoSuchWindowException('Could not find window with expression %s' % expression)
        # Search window marked by current window handle
        if found:
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if self.driver.execute_script('return (self.%s||null)===%s;' % (attribute, json_handle)):
                    return
        self.driver.switch_to.window(current_window_handle)
        raise NoSuchWindowException('Could not find window with expression %s' % expression)

    def _window_is_popup(self):
        """
        Get if current window is popup
        @return: True if current window is popup else False
        """
        return self.driver.execute_script("return !!window.opener;")

    def _selectPopUp(self):
        """
        Select first non-top window
        @raises: NoSuchWindowException
        """
        current_window_handle = self.driver.current_window_handle
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if self._window_is_popup():
                return
        self.driver.switch_to.window(current_window_handle)
        raise NoSuchWindowException('Could not find any popUp')

    def _selectWindow(self, target=None, mode='window'):
        """
        Selenium core's selectWindow and selectPopUp behaves differently, this method provides those two behaviors.

        :param target: selector given to command
        :param mode: either 'popup' or 'window', defaults to 'window'.
        :return:
        """
        # Note: locators' precedence is relevant, see below
        locators = ('var', 'name', 'title') if mode == 'window' else ('name', 'var', 'title')
        current = ('null', '', None)
        tag, value = self._tag_and_value(target, locators=locators, default=None) if target else (None, None)
        if tag == 'name':
            self._selectWindowByName(value)
        elif tag == 'var':
            self._selectWindowByExpression('window.%s' % value)
        elif tag == 'title':
            self._selectWindowByTitle(value)
        elif value in current:
            if mode == 'window':
                self.driver.switch_to.window(self.driver.window_handles[0])  # some backends does not support 0 as param
            elif mode == 'popup':
                self._selectPopUp()
            else:
                raise NotImplementedError('No default for mode %r' % mode)
        else:
            for tag in locators:
                try:
                    self._selectWindow('%s=%s' % (tag, value), mode)
                    break
                except NoSuchWindowException as e:
                    pass
            else:
                raise NoSuchWindowException('Could not find %s with target %s' % (mode, value))
        # windows include popups, but popups don't include windows
        if mode == 'popup' and not self._window_is_popup():
            raise NoSuchWindowException('Could not find %s with target %s' % (mode, value))

    @seleniumcommand
    def selectWindow(self, target, value=None):
        """
        Selects a popup window using a window locator; once a popup window has been selected, all commands go to that
        window. To select the main window again, use null as the target.

        Window locators provide different ways of specifying the window object: by title, by internal JavaScript "name",
        or by JavaScript variable.

            * title=My Special Window: Finds the window using the text that appears in the title bar. Be careful; two
              windows can share the same title. If that happens, this locator will just pick one.
            * name=myWindow: Finds the window using its internal JavaScript "name" property. This is the second
              parameter "windowName" passed to the JavaScript method window.open(url, windowName, windowFeatures,
              replaceFlag) (which Selenium intercepts).
            * var=variableName: Some pop-up windows are unnamed (anonymous), but are associated with a JavaScript
              variable name in the current application window, e.g. "window.foo = window.open(url);". In those cases,
              you can open the window using "var=foo".

        If no window locator prefix is provided, we'll try to guess what you mean like this:
            1. If windowID is null, (or the string "null") then it is assumed the user is referring to the original
               window instantiated by the browser).
            2. If the value of the "windowID" parameter is a JavaScript variable name in the current application window,
               then it is assumed that this variable contains the return value from a call to the JavaScript
               window.open() method.
            3. Otherwise, selenium looks in a hash it maintains that maps string names to window "names".
            4. If that fails, we'll try looping over all of the known windows to try to find the appropriate "title".
               Since "title" is not necessarily unique, this may have unexpected behavior.

        If you're having trouble figuring out the name of a window that you want to manipulate, look at the Selenium log
        messages which identify the names of windows created via window.open (and therefore intercepted by Selenium).
        You will see messages like the following for each window as it is opened:

        debug: window.open call intercepted; window ID (which you can use with selectWindow()) is "myNewWindow"

        In some cases, Selenium will be unable to intercept a call to window.open (if the call occurs during or before
        the "onLoad" event, for example). (This is bug SEL-339.) In those cases, you can force Selenium to notice the
        open window's name by using the Selenium openWindow command, using an empty (blank) url, like this:
        openWindow("", "myFunnyWindow").

        @param target: the JavaScript window ID of the window to select
        """
        self._selectWindow(target, mode='window')

    @seleniumcommand
    def selectPopUp(self, target='null', value=None):
        """
        Simplifies the process of selecting a popup window (and does not offer functionality beyond what selectWindow()
        already provides).

        * If windowID is either not specified, or specified as "null", the first non-top window is selected.
          The top window is the one that would be selected by selectWindow() without providing a windowID.
          This should not be used when more than one popup window is in play.
        * Otherwise, the window will be looked up considering windowID as the following in order:
            1. The "name" of the window, as specified to window.open().
            2. A javascript variable which is a reference to a window.
            3. The title of the window. This is the same ordered lookup performed by selectWindow.

        Important: Selenium core documentation states *WRONGLY*:

            This is the same ordered lookup performed by selectWindow.

        Its wrong because selectPopUp tests name before variable, and selectWindow looks for variable first.

        @param target: an identifier for the popup window, which can take on a number of different meanings
        """
        self._selectWindow(target, mode='popup')

    @seleniumcommand
    def selectFrame(self, target, value=None):
        """
        Selects a frame within the current window. (You may invoke this command multiple times to select nested frames.) To select the parent frame, use "relative=parent" as a locator; to select the top frame, use "relative=top". You can also select a frame by its 0-based index number; select the first frame with "index=0", or the third frame with "index=2".

        You may also use a DOM expression to identify the frame you want directly, like this: dom=frames["main"].frames["subframe"]

        @param target: an element locator identifying a frame or iframe
        """
        if target.startswith('relative='):
            if target[9:] == 'top':
                self.driver.switch_to.default_content()
            elif target[9:] == 'parent':
                raise NotImplementedError('Parent frames can not be located')
            else:
                raise NoSuchFrameException
        else:
            frame = None
            if target.isdigit():
                try:
                    frame = int(target)
                except (ValueError, TypeError):
                    pass
            if frame is None:
                frame = self._find_target(target)
            self.driver.switch_to.frame(frame)

    @seleniumimperative.nowait
    def addLocationStrategy(self, target, value=None):
        self.custom_locators[target] = value

    @seleniumimperative
    def addSelection(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def allowNativeXpath(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumcommand
    def answerOnNextPrompt(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumcommand
    def windowFocus(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def windowMaximize(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def altKeyDown(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def shiftKeyDown(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def controlKeyDown(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def keyDown(self, target, value=None):
        target_elm = self._find_target(target)
        self._chain.key_down(target_elm, value)

    @seleniumimperative
    def keyUp(self, target, value=None):
        target_elm = self._find_target(target)
        self._chain.key_up(target_elm, value)

    @seleniumimperative
    def metaKeyDown(self, target=None, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def metaKeyUp(self, target=None, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseDown(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseDownAt(self, target, value):
        """
        @param target: locator
        @param value: coordstring
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseDownRight(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseDownRightAt(self, target, value):
        """
        @param target: locator
        @param value: coordstring
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseMove(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseMoveAt(self, target, value):
        """
        @param target: locator
        @param value: coordstring
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseUp(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseUpAt(self, target, value):
        """
        @param target: locator
        @param value: coordstring
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseUpRight(self, target, value=None):
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def mouseUpRightAt(self, target, value):
        """
        @param target: locator
        @param value: coordstring
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def openWindow(self, target, value):
        """
        Opens a popup window (if a window with that ID isn't already open). After opening the window, you'll need to select it using the selectWindow command.

        This command can also be a useful workaround for bug SEL-339. In some cases, Selenium will be unable to intercept a call to window.open (if the call occurs during or before the "onLoad" event, for example). In those cases, you can force Selenium to notice the open window's name by using the Selenium openWindow command, using an empty (blank) url, like this: openWindow("", "myFunnyWindow").

        @param target: the URL to open, which can be blank
        @param value: the JavaScript window ID of the window to select
        """
        raise NotImplementedError('not implemented yet')

    @seleniumcommand
    def pause(self, target, value=None):
        """
        Wait for the specified amount of time (in milliseconds)

        @param target: the amount of time to sleep (in milliseconds)
        """
        milliseconds = (int(target) / 1000.) if target else self._timeout
        time.sleep(milliseconds)  # TODO: find a better way

    @seleniumimperative
    def refresh(self, target=None, value=None):
        """
        Simulates the user clicking the "Refresh" button on their browser.
        """
        self.driver.refresh()

    @seleniumimperative
    def removeAllSelections(self, target, value=None):
        """
        Unselects all of the selected options in a multi-select element.

        @param target: an element locator identifying a multi-select box
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def removeScript(self, target, value=None):
        """
        *Important:* This command does nothing as works along with with `addScript` which is unsupported.

        Removes a script tag from the Selenium document identified by the given id. Does nothing if the referenced tag doesn't exist.

        @param target: the id of the script element to remove.
        """
        logger.warn('This command does nothing as works along with with `addScript` which is unsupported.')

    @seleniumimperative
    def removeSelection(self, target, value):
        """
        Remove a selection from the set of selected options in a multi-select element using an option locator. @see #doSelect for details of option locators

        @param target: an element locator identifying a multi-select box
        @param value: an option locator (a label by default)
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def rollup(self, target, value):
        """
        Executes a command rollup, which is a series of commands with a unique name, and optionally arguments that control the generation of the set of commands. If any one of the rolled-up commands fails, the rollup is considered to have failed. Rollups may also contain nested rollups.

        @param target: the name of the rollup command
        @param value: keyword arguments string that influences how the rollup expands into commands
        """
        raise NotImplementedError('not implemented yet')

    @seleniumimperative
    def runScript(self, target, value=None):
        """
        Creates a new "script" tag in the body of the current test window, and adds the specified text into the body of the command. Scripts run in this way can often be debugged more easily than scripts executed using Selenium's "getEval" command. Beware that JS exceptions thrown in these script tags aren't managed by Selenium, so you should probably wrap your script in try/catch blocks if there is any chance that the script will throw an exception.

        @param target: the JavaScript snippet to run
        """
        self._writeScript(value, where='body')

    @seleniumimperative
    def addScript(self, target, value=None):
        """
        *Important:* Not implemented as it's not supported by Selenium IDE itself, see: https://code.google.com/p/selenium/issues/detail?id=5998

         Loads script content into a new script tag in the Selenium document. This differs from the runScript command in that runScript adds the script tag to the document of the AUT, not the Selenium document. The following entities in the script content are replaced by the characters they represent: < > & The corresponding remove command is removeScript.

        scriptContent - the Javascript content of the script to add
        scriptTagId - (optional) the id of the new script tag. If specified, and an element with this id already exists, this operation will fail.
        """
        raise NotImplementedError('Unsupported by Selenium IDE and unable to get Selenium document using webdriver.')

    def _selector_from_element(self, element):
        """
        Get unique css selector from selenium element (or locator)
        @param element: selenium element or locator
        @return:spath as string
        """
        if isinstance(element, six.string_types):
            element = self._find_target(element)

        hierarchy = []
        with element_context(element):
            element = original_element(element)
            try:
                while True:
                    parent = element.find_element_by_xpath('..')
                    siblings = parent.find_elements_by_xpath(element.tag_name)
                    hierarchy.append('%s:nth-of-type(%d)' % (element.tag_name, siblings.index(element) + 1))
                    element = parent
            except InvalidSelectorException:
                # Ignore if triggered by find_element_by_xpath('..') on parent nodes
                if self.driver.find_element_by_xpath('/%s' % element.tag_name)._id != element._id:
                    raise
            hierarchy.append(element.tag_name)
        hierarchy.reverse()
        return ' > '.join(hierarchy)

    def _element_from_soup(self, element):
        """
        Get selenium object pointing to given soup element
        @param element: bs4.element.Tag
        @return: selenium element
        """
        components = []
        child = element if element.name else element.parent
        for parent in child.parents:
            previous = itertools.islice(parent.children, 0, parent.contents.index(child))
            xpath_tag = child.name
            xpath_index = sum(1 for i in previous if i.name == xpath_tag) + 1
            components.append(xpath_tag if xpath_index == 1 else '%s[%d]' % (xpath_tag, xpath_index))
            child = parent
        components.reverse()
        return self._find_target('xpath=/%s' % '/'.join(components))

    def _soup_from_element(self, element):
        """
        Get BeautifulSoup element from selenium element (or locator)
        @param element: selenium element or locator
        @return: BeautifulSoup element
        """
        if isinstance(element, six.string_types):
            element = self._find_target(element)

        try:
            css = self._selector_from_element(element)
        except NOT_PRESENT_EXCEPTIONS:
            raise NoSuchElementException('Element disappeared from tree while running command.')

        with element_context(element):
            source = self.driver.page_source

        return beautifulsoup.BeautifulSoup(source).select(css)[0]

    @seleniumgeneric
    def TextPresent(self, target, value=None):
        """
        Verify that the specified text pattern appears somewhere on the page shown to the user (if visible).
        @param target: a pattern to match with the text of the page
        @param value: <not used>
        @return true if the pattern matches the text, false otherwise
        """
        doc = beautifulsoup.BeautifulSoup(self.driver.page_source).body
        for result in doc.findAll(text=self._translatePatternToRegex(target)):
            if self._element_from_soup(result).is_displayed():
                return True, True
        return True, False

    @seleniumgeneric
    def Title(self, target=None, value=None):
        """
        Gets the title of the current page.
        @param target: <not used>
        @param value: <not used>
        @return the title of the current page
        """
        return target, self.driver.title

    @seleniumgeneric
    def Location(self, target, value=None):
        """
        Get absolute url of current page
        @param target:
        @param value: <not used>
        """
        return target, self.driver.current_url

    @seleniumgeneric
    def Visible(self, target, value=None):
        """
        Get if element for given locator is visible
        @param target:
        @param value: <not used>
        """
        try:
            return True, self._find_target(target).is_displayed()
        except NOT_PRESENT_EXCEPTIONS:
            return True, False

    @seleniumgeneric
    def ElementPresent(self, target, value=None):
        """
        Verify that the specified element is somewhere on the page. Catch a NoSuchElementException in order to return a result.
        @param target: an element locator
        @param value: <not used>
        @return true if the element is present, false otherwise
        """
        try:
            self._find_target(target)
            return True, True
        except NOT_PRESENT_EXCEPTIONS:
            return True, False

    @seleniumgeneric
    def Attribute(self, target, value):
        """
        Get the value of an element attribute.
        @param target: an element locator followed by an @ sign and then the name of the attribute, e.g. "foo@bar"
        @param value: the expected value of the specified attribute
        @return the value of the specified attribute
        """
        target, sep, attr = target.rpartition("@")
        attrValue = self._find_target(target).get_attribute(attr)
        if attrValue is None:
            raise NoSuchAttributeException(attr)
        return value, attrValue.strip()

    @seleniumgeneric
    def Expression(self, target, value):
        """
        Get given expression value
        @param target: value to store
        @param value: variable name
        @return the value of the specified attribute
        """
        return value, target

    @seleniumgeneric
    def Eval(self, target, value):
        """
        Get value returned by given javascript expression
        @param target: value to store
        @param value: variable name
        @return the value of the specified attribute
        """
        reset = ['document']  # ensure consistent behavior
        js = (
            'var %(reset)s,'
                'storedVars=%(variables)s,'
                'r = eval(%(target)s);'
            # We need to care about Selenium IDE returning 'null' instead of 'undefined'.
            'return [\'\'+(r===undefined?null:r), storedVars];'
            ) % {
            'reset': ','.join('%s = undefined' % i for i in reset),
            'variables': json.dumps(self.storedVariables),
            'target': json.dumps(target),
            }
        result, self.storedVariables = self.driver.execute_script(js)
        return value, result

    @seleniumgeneric
    def Text(self, target, value):
        """
        Get the text of an element. This works for any element that contains text, even if not visible.
        @param target: an element locator
        @param value: the expected text of the element
        @return the text of the element
        """
        if isinstance(self.driver, selenium.webdriver.Firefox):
            # extremely slow workaround to https://code.google.com/p/selenium/issues/detail?id=8390
            soup = self._soup_from_element(target)
            return value, soup.get_text().strip()

        js = 'return arguments[0].textContent||arguments[0].innerText||"";'
        element = self._find_target(target)
        with element_context(element):
            element = original_element(element)
            return value, self.driver.execute_script(js, element).strip()

    @seleniumgeneric
    def Value(self, target, value):
        """
        Get the value of an input field (or anything else with a value parameter).
        @param target: an element locator
        @param value: the expected element value
        @return the element value
        """
        return value, self._find_target(target).get_attribute("value").strip()

    @seleniumgeneric
    def XpathCount(self, target, value):
        """
        Get the number of nodes that match the specified xpath, e.g. "//table" would give the number of tables.
        @param target: an xpath expression to locate elements
        @param value: the number of nodes that should match the specified xpath
        @return the number of nodes that match the specified xpath
        """
        count = len(self.driver.find_elements_by_xpath(target))
        return (int(value) if value else count), count

    @seleniumgeneric.nowait
    def Alert(self, target, value=None):
        """
        Retrieve the message of a JavaScript alert generated during the previous action, or fail if there are no alerts.
        Getting an alert has the same effect as manually clicking OK. If an alert is generated but you do not consume it
        with getAlert, the next webdriver action will fail.
        @param target: the expected message of the most recent JavaScript alert
        @param value: <not used>
        @return the message of the most recent JavaScript alert
        """
        alert = self.driver.switch_to.alert
        try:
            text = alert.text.strip()
            alert.accept()
            return target, text
        except WebDriverException:
            logger.error('WebDriverException, maybe caused by driver not supporting Alert control.')
            raise

    @seleniumgeneric.nowait
    def Confirmation(self, target, value=None):
        # TODO: implement properly
        alert = Alert(self.driver)
        try:
            text = alert.text.strip()
            alert.accept()
            return target, text
        except WebDriverException:
            logger.error('WebDriverException, maybe caused by driver not supporting Alert control.')
            raise


    @seleniumgeneric
    def Table(self, target, value):
        """
        Get the text from a cell of a table. The cellAddress syntax is tableLocator.row.column, where row and column start at 0.
        @param target: a cell address, e.g. "css=#myFirstTable.2.3"
        @param value: the text which is expected in the specified cell.
        @return the text from the specified cell
        """
        target, row, column = target.rsplit(".", 2)
        table = self._find_target(target)
        rows = []
        # collect all rows  from the possible table elements in the needed order
        # TODO: traverse tr and th/td correctly
        for tableElem in ['thead', 'tbody', 'tfoot']:
            rows.extend(table.find_elements_by_xpath(tableElem + '/*'))
        # get the addressed child element of the addressed row
        cell = rows[int(row)].find_elements_by_xpath('*')[int(column)]
        return value, cell.text.strip()

    _tag_value_re = re.compile(r'(?P<tag>[a-zA-Z0-9_]+)=(?P<value>.*)')

    @classmethod
    def _tag_and_value(cls, target, locators=None, default=None):
        """
        Get the tag of an element locator to identify its type, if not tag is found, return default.

        Locators are tested against `locators` iterable parameter.
        If `locators` is dict, its value is called if callable (with tag and value as parameters) or used for
        string formating (if tuple of strings, with 'tag' and 'value' variables). None value means no action.

        @param target: an element locator
        @param locators: optional iterable of locators, if dict, values can be None, callable or tuple of str.
        @param default: default locator, defaults to None
        @return an element locator splited into its tag and value.

        """
        match = cls._tag_value_re.match(target)
        if match:
            group = match.groupdict()
            tag = group['tag']
            value = group['value']
        else:
            tag = default
            value = target

        if locators is None:
            return tag, value

        if not tag in locators:
            if tag == default:
                return tag, value
            raise UnexpectedTagNameException('invalid locator format "%s"' % tag)

        if not isinstance(locators, dict):
            return tag, value

        if locators[tag] is None:
            return tag, value

        if callable(locators[tag]):
            return locators[tag](tag, value)

        param = {'tag': tag, 'value': value}
        return locators[tag][0] % param, locators[tag][1] % param

    def _find_target(self, target, click=False):
        """
        Select and execute the appropriate find_element_* method for an element locator.
        @param target: an element locator
        @return the webelement instance found by a find_element_* method
        @rtype: selenium.webdriver.remote.webelement.WebElement
        """
        if self.custom_locators:
            template = '(function(locator, inWindow, inDocument){%s}(\'%s\', window, window.document));'
            locators = dict(self._target_locators)
            locators.update((name, ('dom', template % body)) for name, body in six.iteritems(self.custom_locators))
        else:
            locators = self._target_locators

        tag, value = self._tag_and_value(target, locators=locators, default='identifier')
        if tag == 'ui':
            raise NotImplementedError('ui locators are not implemented yet')  # TODO: implement
        elif tag == 'css':
            find_one = functools.partial(self.driver.find_element_by_css_selector, value)
            find_many = functools.partial(self.driver.find_elements_by_css_selector, value)
        elif tag == 'dom':
            find_one = functools.partial(self.driver.execute_script, 'return eval(%s)' % json.dumps(value))
            find_many = find_one
        elif tag in self._by_target_locators:
            by = self._by_target_locators[tag]
            find_one = functools.partial(self.driver.find_element, by, value)
            find_many = functools.partial(self.driver.find_elements, by, value)
        else:
            raise NotImplementedError('No support for %r locators' % tag)

        if click:
            # Selenium IDE filters for clickable items on click commands, so ambiguous locators which matches both
            # clickable and unclickable items should not fail.
            for element in find_many():
                if element.is_displayed() and element.is_enabled():
                    return element
        else:
            try:
                return find_one()
            except NOT_PRESENT_EXCEPTIONS:
                pass

        # Search for element in iframes (done by default in Selenium IDE)
        for iframe in self.driver.find_elements_by_tag_name('iframe'):
            with ExternalContext(self.driver, iframe):
                try:
                    return ExternalElement.from_webelement(self._find_target(target), iframe)
                except NOT_PRESENT_EXCEPTIONS:
                    pass

        # Not found, raise
        raise NoSuchElementException('Element with %r not found.' % value)

    _simplify_spaces = re.compile(r'\n\s+')

    @classmethod
    def _matches(cls, expectedResult, result):
        """
        Try to match a result of a selenese command with its expected result.
        The function performs a plain equality comparison for non-Strings and handles all three kinds of String-match patterns which Selenium defines:
        1) plain equality comparison
        2) exact: a non-wildcard expressions
        3) regexp: a regular expression
        4) glob: a (possible) wildcard expression. This is the default (fallback) method if 1), 2) and 3) don't apply
        see: http://release.seleniumhq.org/selenium-remote-control/0.9.2/doc/dotnet/Selenium.html    
        @param expectedResult: the expected result of a selenese command
        @param result: the actual result of a selenese command
        @return true if matches, false otherwise
        """
        if not isinstance(expectedResult, six.string_types):  # equality for booleans, integers, etc
            return expectedResult == result
        # Normalize line separators
        expectedResult = cls._simplify_spaces.sub('\n ', expectedResult)
        result = cls._simplify_spaces.sub('\n ', result)
        if expectedResult.startswith("exact:"):
            return result == expectedResult[6:]
        match = cls._translatePatternToRegex(expectedResult).match(result)
        return False if match is None else result == match.group(0)

    @classmethod
    def _translatePatternToRegex(cls, pat):
        """
        Various Pattern syntaxes are available for matching string values:

            * *glob:pattern* Match a string against a "glob" (aka "wildmat") pattern. "Glob" is a kind of limited regular-expression syntax typically used in command-line shells. In a glob pattern, "*" represents any sequence of characters, and "?" represents any single character. Glob patterns match against the entire string.
            * *regexp:pattern* Match a string using a regular-expression. The full power of JavaScript regular-expressions is available.
            * *regexpi:regexpi* Match a string using a case-insensitive regular-expression.
            * *xact:string* Match a string exactly, verbatim, without any of that fancy wildcard stuff.
If no pattern prefix is specified, Selenium assumes that it's a "glob" pattern.

            For commands that return multiple values (such as verifySelectOptions), the string being matched is a comma-separated list of the return values, where both commas and backslashes in the values are backslash-escaped. When providing a pattern, the optional matching syntax (i.e. glob, regexp, etc.) is specified once, as usual, at the beginning of the pattern.

        @param pat: pattern
        @return: python compiled regexp (instance of _sre.SRE_Pattern)
        """
        if pat.startswith('regexp:'):
            repat = re.compile(pat[7:])
        elif pat.startswith('regexpi:'):
            repat = re.compile(pat[7:], re.IGNORECASE)
        elif pat.startswith("exact:"):
            # exact means no-wildcard, not regexp's line match
            repat = re.compile(re.escape(pat[6:]))
        else:
            if pat.startswith("glob:"):  # glob and wildcards
                pat = pat[5:]
            repat = cls._translateWilcardToRegex(pat)
        return repat

    _wildcardTranslations = {
        re.compile(r"(?<!\\)\\\*"): r".*",
        re.compile(r"(?<!\\)\\\?"): r".",
    }

    @classmethod
    def _translateWilcardToRegex(cls, wc):
        """
        Translate a wildcard pattern into in regular expression (in order to search with it in Python).
        Note: Since the IDE wildcard expressions do not support bracket expressions they are not handled here.
        @param wc: a wildcard pattern
        @return the translation into a regular expression.
        """
        if wc.endswith('...'):
            wc = '%s*' % wc[:-3]
        wc = re.escape(wc)
        for expr, final in six.iteritems(cls._wildcardTranslations):
            wc = expr.sub(final, wc)
        return re.compile(wc)
