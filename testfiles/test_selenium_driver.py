"""
UT module to test selenium-driver commands
"""
import sys
import pytest
import logging

from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException, UnexpectedTagNameException, \
    NoSuchFrameException, NoSuchAttributeException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

sys.path.insert(0, '..')

from selexe import selenium_driver, selexe_runner                                                          # noqa
from environment import SELEXE_DRIVER, SELEXE_TIMEOUT, SELEXE_BASEURI, PHANTOMJS_PATH, SELEXE_SKIP_ALERT   # noqa

logger = logging.getLogger(__name__)


class Test_SeleniumDriver:
    def setup_method(self, _):
        driver_options = {}
        if SELEXE_DRIVER == 'phantomjs':
            driver_options['executable_path'] = PHANTOMJS_PATH
        self.driver = selexe_runner.SelexeRunner.webdriver_classes[SELEXE_DRIVER](**driver_options)
        self.sd = selenium_driver.SeleniumDriver(self.driver, baseuri=SELEXE_BASEURI, timeout=SELEXE_TIMEOUT)
        self.exe = self.sd.execute

    def teardown_method(self, _):
        self.driver.quit()

    def test_all_Text_methods(self):
        """check getText / verifyText / assertText / storeText / ... methods"""
        self.exe('open', '/static/page1')
        assert self.exe('getText', 'css=h1') == 'H1 text'
        #
        self.exe('verifyText', 'css=h1', 'H1 text')
        assert not self.sd.verification_errors
        #
        # check failing verifyText command:
        self.exe('verifyText', 'css=h1', 'H1 WROOOOOONG text')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        # check failing verfiyNotText command:
        self.exe('verifyNotText', 'css=h1', 'H1 text')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        self.exe('assertText', 'css=h1', 'H1 text')
        #
        # check that wrong text raises AssertionError
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that correct text raises AssertionError for 'assertNotText'
        with pytest.raises(AssertionError):
            self.exe('assertNotText', 'css=h1', 'H1 text')
        #
        self.exe('storeText', 'css=h1', 'h1content')
        assert self.sd.storedVariables['h1content'] == 'H1 text'
        self.exe('assertText', 'css=h1', '${h1content}')
        #
        # check that a NoSuchElmenentException is not caught
        with pytest.raises(NoSuchElementException):
            self.exe('verifyText', '//p[@class="class"]')
        #
        # check the waitFor methods
        #
        # check waiting for an existent text
        self.exe('waitForText', 'css=h1', 'H1 text')
        #
        # check that waiting for non-existing text finally raises TimeoutException
        with pytest.raises(TimeoutException):
            self.exe('waitForText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that waiting for existing text with 'waitForNotText' raises TimeoutException
        with pytest.raises(TimeoutException):
            self.exe('waitForNotText', 'css=h1', 'H1 text')

        # check waiting for text which is inserted on the page 500 ms after clicking on a button
        self.sd.timeout = 1000
        self.exe('click', 'id=textInsertDelay')
        self.exe('waitForTextPresent', 'Text was inserted')
        #
        # check waiting for a text which is deleted on the page 500 ms after clicking on a button
        self.exe('click', 'id=textRemoveDelay')
        self.exe('waitForNotTextPresent', 'Text was inserted')
        self.sd.timeout = SELEXE_TIMEOUT
        #
        # check that waiting for non-existing text finally raises TimeoutException
        with pytest.raises(TimeoutException):
            self.exe('waitForText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that waiting for existing text with 'waitForNotText' raises aTimeoutException
        with pytest.raises(TimeoutException):
            self.exe('waitForNotText', 'css=h1', 'H1 text')

    def test_Alert_methods(self):
        """check alert methods"""
        if SELEXE_SKIP_ALERT:
            # phantomJS does not support alerts, so we added an option for deactivating them
            logger.warning('Alert tests have been deactivated by environ')
            return

        # check that an alert can be found
        self.exe('open', '/static/page1')
        self.exe('click', '//input[@type="button" and @value="alert button"]')
        self.exe('assertAlert', 'hello')
        #
        # check that a missing alert raises an exception
        with pytest.raises(NoAlertPresentException):
            self.exe('assertAlert', 'hello')
        #
        # check that a wrong alert text adds a verification error
        self.exe('click', '//input[@value="alert button"]')
        self.exe('verifyAlert', 'a wrong text')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        # check that a missing alert adds a verification error (added by verify wrapper)
        self.exe('verifyAlert', 'hello')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        # check that a missing alert adds a verification error (added by verifyNot wrapper)
        self.exe('verifyNotAlert', 'hello')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        # Check that the message of the alert window gets stored
        self.exe('click', '//input[@value="alert button"]')
        self.exe('storeAlert', 'alertmsg')
        assert self.sd.storedVariables['alertmsg'] == 'hello'
        #
        # check the confirmation method which is an alias for the alert method
        self.exe('click', '//input[@value="alert button"]')
        self.exe('assertConfirmation', 'hello')

    def test_XpathCount_method(self):
        """check the XpathCount method and the associated find_targets method"""
        self.exe('open', '/static/form1')
        # note: this method returns two integers (instead of strings or booleans like all the other return methods)
        #
        self.exe('assertXpathCount', '//option', "4")
        #
        # check failing for incorrect number of xpathes
        self.exe('verifyXpathCount', '//option', "3")
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages

    def test_Select_method(self):
        """check select method and the associated find_children method (for selection lists / drop-downs)"""
        self.exe('open', '/static/form1')
        #
        # check finding option elements by given id of the select node
        self.exe('select', 'id=selectTest', "value=value1")
        #
        # check finding option elements by given xpath of the select node
        self.exe('select', '//select', "value=value2")
        #
        # check finding option elements by given name of the select node
        self.exe('select', 'name=select1', "value=value3")
        #
        # check finding option elements by given css path of the select node
        self.exe('select', 'css=#selectTest', "value=value4")
        #
        # check that all option locator parameters work as expected
        optionLocators = [('label1', '1'), ('label=label2', '2'), ('value=value3', '3'),
                          ('id=option4', '4'), ('index=0', '1')]
        for optionLocator in optionLocators:
            self.exe('select', 'id=selectTest', optionLocator[0])
            self.exe('assertAttribute', '//select[@id="selectTest"]/option[' + optionLocator[1] + "]@selected", "true")
        #
        # check failing using unknown option locator parameter
        with pytest.raises(UnexpectedTagNameException):
            self.exe('select', 'id=selectTest', 'xpath=//option[@id="option3"]')
        #
        # check failing with correct option locator parameters but incorrect values
        for optionLocator in ['label', 'label=2', 'value=value', 'id=optio4', 'index=4']:
            with pytest.raises(NoSuchElementException):
                self.exe('select', 'id=selectTest', optionLocator)
        #
        # check failing while trying to perform a select command on a non-select element
        with pytest.raises(UnexpectedTagNameException):
            self.exe('select', 'id=id_submit', "value=value1")

    def test_Check_methods(self):
        """test the uncheck and check method (for checkboxes)"""
        self.exe('open', '/static/form1')
        #
        # verify that checkbox1 is unchecked
        with pytest.raises(NoSuchAttributeException):
            self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform a check command on unchecked checkbox1
        self.exe('check', '//*[@value="first"]')
        #
        # verify that checkbox1 is checked
        self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform a check command on checked checkbox1
        self.exe('check', '//*[@value="first"]')
        #
        # verify that checkbox1 is (still) checked
        self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform an uncheck command on checked checkbox1
        self.exe('uncheck', '//*[@value="first"]')
        #
        # verify that checkbox1 is unchecked
        with pytest.raises(NoSuchAttributeException):
            self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform an uncheck command on unchecked checkbox1
        self.exe('uncheck', '//*[@value="first"]')
        #
        # verify that checkbox1 is (still) unchecked
        with pytest.raises(NoSuchAttributeException):
            self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')

    def test_Mouse_methods(self):
        """check the mouseOver and mouseOut methods"""
        self.exe('open', '/static/form1')
        #
        # check that checkbox1 is unchecked
        with pytest.raises(NoSuchAttributeException):
            self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # hover the mouse over checkbox1
        self.exe('mouseOver', '//*[@name="checkbox1"]')
        #
        # click on the current position
        ActionChains(self.driver).click().perform()
        #
        # verify that checkbox1 is checked now
        self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # move the mouse away from checkbox1
        self.exe('mouseOut', '//*[@name="checkbox1"]')
        #
        # click on the current position
        ActionChains(self.driver).click().perform()
        #
        # verify that checkbox1 is (still) checked
        self.exe('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')

    def test_Aliases(self):
        """In the IDE there are aliases for "Not" commands which were generated automatically from commands
        with prefix "is_" (most likely to increase readability). We do the same."""
        self.exe('open', '/static/page1')
        self.exe('verifyTextNotPresent', 'H1 texts')
        self.exe('assertElementNotPresent', 'id=select')
        self.exe('waitForTextNotPresent', 'H1 texts')

    def test_PopUp_methods(self):
        """check the waitForPopUp and selectWindow methods"""
        self.exe('open', '/static/page1')
        #
        # open a pop up by clicking on a link
        self.exe('click', 'link=Test popup')
        #
        # check waiting for the pop up with standard timeout
        self.exe('waitForPopUp', "stekie")
        #
        # check that the focus is still on the main window.
        assert self.exe('getText', 'css=h1') == 'H1 text'
        #
        # check waiting for a non-existent pop up with specified timeout = 0.5s
        with pytest.raises(TimeoutException):
            self.exe('waitForPopUp', "no pop up", "500")
        #
        # check selecting "null" as target (any popup)
        self.exe('waitForPopUp')
        #
        # switch focus to the pop up
        self.exe('selectWindow', "name=stekie")
        #
        # check that text in the pop up can be found.
        assert self.exe('isTextPresent', 'This is a pop up')
        #
        # switch focus back to the main window
        self.exe('selectWindow', "null")
        assert self.exe('getText', 'css=#h1_1') == 'H1 text'
        self.exe('assertNotTextPresent', 'This is a pop up')
        #
        # check using a locator parameter
        self.exe('selectWindow', "stekie")

    def test_ElementPresent_method(self):
        self.exe('open', '/static/page1')
        """check the elementPresent method"""
        #
        # check that an element can be found
        self.exe('verifyElementPresent', '//div[@class="class1"]')
        assert not self.sd.verification_errors
        #
        # check that a missing element adds a verification error
        self.exe('verifyElementPresent', '//div[@class="class"]')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        # check that an element which should not be present adds a verification error
        self.exe('verifyNotElementPresent', '//div[@class="class1"]')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        # check that a missing element raises an assertion error and not a NoSuchElementException:
        with pytest.raises(AssertionError):
            self.exe('assertElementPresent', '//div[@class="class"]')
        #
        # check the storing of the result of the ElementPresent method
        self.exe('storeElementPresent', '//div[@class="class"]', 'elementPresent')
        assert self.sd.storedVariables['elementPresent'] is False

    def test_SeleniumStringPatterns(self):
        """testing string match parameters regexp, exact and glob in _match and _isContained methods"""
        self.exe('open', '/static/page1')
        self.exe('getText', 'css=h1', 'regexp:H1 text')
        #
        # method: _match / parameter: regexp
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', 'regexp:H1 tex')
        self.exe('assertText', 'css=h1', 'regexp:H1 text')
        self.exe('assertText', 'css=h1', r'regexp:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', 'regexp:H1*text')
        #
        # method: _match / parameter: exact
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', 'ecact:H1 tex')
        self.exe('assertText', 'css=h1', 'exact:H1 text')
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', r'exact:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', 'exact:H1*text')
        #
        # method: _match / parameter: glob
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', 'glob:H1 tex')
        self.exe('assertText', 'css=h1', 'glob:H1 text')
        with pytest.raises(AssertionError):
            self.exe('assertText', 'css=h1', r'glob:H.* tex\w+')
        self.exe('assertText', 'css=h1', 'glob:H1*text')
        #
        # method: _isContained / parameter: regexp
        self.exe('assertTextPresent', 'regexp:H1 tex')
        self.exe('assertTextPresent', 'regexp:H1 text')
        self.exe('assertTextPresent', r'regexp:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.exe('assertTextPresent', 'regexp:H1*text')
        #
        # method: _isContained / parameter: exact
        self.exe('assertTextPresent', 'exact:H1 tex')
        self.exe('assertTextPresent', 'exact:H1 text')
        with pytest.raises(AssertionError):
            self.exe('assertTextPresent', r'exact:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.exe('assertTextPresent', 'exact:H1*text')
        #
        # method: _isContained / parameter: glob
        self.exe('assertTextPresent', 'glob:H1 tex')
        self.exe('assertTextPresent', 'glob:H1 text')
        with pytest.raises(AssertionError):
            self.exe('assertTextPresent', r'glob:H.* tex\w+')
        self.exe('assertTextPresent', 'glob:H1*text')
        #
        # method: unicode selector and text plus exact
        self.exe('assertTextPresent', u'Unicode character \xd1')
        self.exe('assertText', u'link=Unicode character \xd1', u'Unicode character \xd1')
        self.exe('assertText', u'link=Unicode character \xd1', u'exact:Unicode character \xd1')
        with pytest.raises(AssertionError):
            self.exe('assertText', u'link=Unicode character \xd1', u'Udnicode character \xd1')

    def test_missing_and_unknown_locator_parameter(self):
        self.exe('open', '/static/form1')
        #
        # check that a missing locator parameter is resolved to name
        self.exe("assertElementPresent", "text1")
        #
        # check that a missing locator parameter is resolved to id
        self.exe("assertElementPresent", "id_text1")
        #
        # check that an unknown parameter raises an Unexpected TagNameException
        with pytest.raises(UnexpectedTagNameException):
            self.exe("assertElementPresent", "value=first")

    def test_SelectFrame_method(self):
        """ testing the selectFrame method"""
        self.exe('open', '/static/page2')
        #
        # check that text in iframe1 cannot be found
        self.exe("assertTextNotPresent", "This is a text inside the first iframe")
        #
        # select iframe1
        self.exe("selectFrame", "id=iframe1")
        #
        # check that the text in iframe1 can be found
        self.exe("assertTextPresent", "This is a text inside the first iframe")
        #
        # select iframe3 (nested in iframe1)
        self.exe("selectFrame", "id=iframe3")
        #
        # check that the text in iframe3 can be found
        self.exe("assertTextPresent", "This is a text inside the third iframe")
        #
        # check the relative parameter: parent selection is not implemented yet
        with pytest.raises(NotImplementedError):
            self.exe("selectFrame", "relative=parent")
        #
        # check the relative parameter: select the top frame
        self.exe("selectFrame", "relative=top")
        #
        # check that a text in the top frame can be found
        self.exe("assertTextPresent", "Default content")
        #
        # select iframe2 by index
        self.exe("selectFrame", "1")
        #
        # check that the text in iframe2 can be found
        self.exe("assertTextPresent", "This is a text inside the second iframe")
        #
        # check that unknown relative parameter raises a NoSuchFrameException
        with pytest.raises(NoSuchFrameException):
            self.exe("selectFrame", "relative=child")

    def test_Value_and_Attribute_method(self):
        """ testing the value and attribute method"""
        self.exe('open', '/static/form1')
        #
        # check that the value of the 'value' attribute can be found and is correct
        self.exe('assertValue', 'id=id_text1', 'input_text1')
        #
        # check that a wrong value adds a verification error
        self.exe('verifyValue', 'id=id_text1', '')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages
        #
        # check that the value of the 'type' attribute can be found and is correct
        self.exe('assertAttribute', 'id=id_submit@type', 'submit')
        #
        # check that a wrong value adds a verification error
        self.exe('verifyAttribute', 'id=id_submit@type', 'submits')
        assert self.sd.verification_errors
        self.sd.clean_verification_errors()  # reset verification messages

    def test_Type_method(self):
        """ testing the type method"""
        self.exe('open', '/static/form1')
        #
        # type a string into an empty text field
        self.exe('type', 'id=id_text1', 'a new text')
        #
        # assert that the text field's value attribute was filled correctly
        assert self.exe('getAttribute', 'id=id_text1@value') == 'a new text'

    def test_Table_method(self):
        """ testing the table method"""
        self.exe('open', '/static/page3')
        #
        # searching in a table with only a tbody element
        self.exe('assertTable', 'css=table#firstTable.2.2', 'Manchester')
        #
        # searching in a table with thead and tbody elements. The order of these elements in the html code
        # does not correspond to the displayed order and thus the search address.
        self.exe('assertTable', 'css=table#secondTable.2.2', 'Manchester')
        #
        # searching in a table with thead, tbody and tfoot elements. The order of these elements in the
        # html code does not correspond to the displayed order and thus the search address.
        self.exe('assertTable', 'css=table#thirdTable.2.2', 'London')

    def test_Command_NotImplementedError(self):
        """ checking that a non-existent command raises a NotImplementedError"""
        with pytest.raises(NotImplementedError):
            self.exe('myNewCommand', 'action')
