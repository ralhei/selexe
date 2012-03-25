"""
UT module to test selenium-driver commands
"""
import sys, py.test
sys.path.insert(0, '..')
###
from selenium import webdriver
from selexe import selenium_driver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import UnexpectedTagNameException
from selenium.common.exceptions import NoSuchFrameException
from selenium.common.exceptions import NoSuchAttributeException
from selenium.webdriver.common.action_chains import ActionChains

from test_execute_sel_files import setup_module, teardown_module

BASE_URI = 'http://localhost:8080'


class Test_SeleniumDriver(object):
    def setup_method(self, method):
        self.driver = webdriver.Firefox()
        self.sd = selenium_driver.SeleniumDriver(self.driver, BASE_URI)
        self.sd.setTimeoutAndPoll(1000, 1) # during testing only wait 1sec until timeout should be raised

    def teardown_method(self, method):
        self.driver.quit()

    def test_all_Text_methods(self):
        """check getText / verifyText / assertText / storeText / ... methods"""
        self.sd('open', '/static/page1')
        #
        assert self.sd('getText', 'css=h1') == 'H1 text'
        #
        self.sd('verifyText', 'css=h1', 'H1 text')
        assert self.sd.getVerificationErrors() == []
        #
        # check failing verifyText command:
        self.sd('verifyText', 'css=h1', 'H1 WROOOOOONG text')
        assert self.sd.getVerificationErrors() == ['Actual value "H1 text" did not match "H1 WROOOOOONG text"']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # check failing verfiyNotText command:
        self.sd('verifyNotText', 'css=h1', 'H1 text')
        assert self.sd.getVerificationErrors() == ['Actual value "H1 text" did match "H1 text"']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        self.sd('assertText', 'css=h1', 'H1 text')
        #
        # check that wrong text raises AssertionError
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that correct text raises AssertionError for 'assertNotText'
        with py.test.raises(AssertionError):
            self.sd('assertNotText', 'css=h1', 'H1 text')
        #
        self.sd('storeText', 'css=h1', 'h1content')
        assert self.sd.storedVariables['h1content'] == 'H1 text'
        self.sd('assertText', 'css=h1', '${h1content}')
        #
        # check that a NoSuchElmenentException is not caught
        with py.test.raises(NoSuchElementException):
            self.sd('verifyText', '//p[@class="class"]')  
        #
        # check the waitFor methods
        #
        # check waiting for an existent text
        self.sd('waitForText', 'css=h1', 'H1 text')
        #
        # check that waiting for non-existing text finally raises RuntimeError (after timeout):
        with py.test.raises(RuntimeError):
            self.sd('waitForText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that waiting for existing text with 'waitForNotText' raises RuntimeError (after timeout)
        with py.test.raises(RuntimeError):
            self.sd('waitForNotText', 'css=h1', 'H1 text')
            
        # check waiting for text which is inserted on the page 2000 ms after clicking on a button
        self.sd.setTimeoutAndPoll(5000, 0.2)
        self.sd('click', 'id=textInsertDelay')
        self.sd('waitForTextPresent', 'Text was inserted')
        #
        # check waiting for a text which is deleted on the page 2000 ms after clicking on a button
        self.sd('click', 'id=textRemoveDelay')
        self.sd('waitForNotTextPresent', 'Text was inserted')
        self.sd.setTimeoutAndPoll(1000, 1)
        #
        # check that waiting for non-existing text finally raises RuntimeError a (after timeout):
        with py.test.raises(RuntimeError):
            self.sd('waitForText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that waiting for existing text with 'waitForNotText' raises a RuntimeError (after timeout)
        with py.test.raises(RuntimeError):
            self.sd('waitForNotText', 'css=h1', 'H1 text')

             

    def test_Alert_methods(self):
        """check alert methods"""
        # check that an alert can be found
        self.sd('open', '/static/page1')
        self.sd('clickAndWait', '//input[@type="button" and @value="alert button"]')
        self.sd('assertAlert', 'hello')
        #
        # check that a missing alert raises an exception
        with py.test.raises(NoAlertPresentException):
            self.sd('assertAlert', 'hello')
        #
        # check that a wrong alert text adds a verification error
        self.sd('click', '//input[@value="alert button"]')
        self.sd('verifyAlert', 'a wrong text')
        assert self.sd.getVerificationErrors() == ['Actual value "hello" did not match "a wrong text"']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # check that a missing alert adds a verification error (added by verify wrapper)     
        self.sd('verifyAlert', 'hello')
        assert self.sd.getVerificationErrors() == ['There were no alerts or confirmations']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # check that a missing alert adds a verification error (added by verifyNot wrapper)   
        self.sd('verifyNotAlert', 'hello')
        assert self.sd.getVerificationErrors() == ['There were no alerts or confirmations']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # Check that the message of the alert window gets stored
        self.sd('click', '//input[@value="alert button"]')
        self.sd('storeAlert', 'alertmsg')
        assert self.sd.storedVariables['alertmsg'] == 'hello'
        #
        # check the confirmation method which is an alias for the alert method
        self.sd('click', '//input[@value="alert button"]')
        self.sd('assertConfirmation', 'hello')

            
    def test_XpathCount_method(self):
        """check the XpathCount method and the associated find_targets method"""
        self.sd('open', '/static/form1')
        # note: this method returns two integers (instead of strings or booleans like all the other return methods)
        #
        self.sd('assertXpathCount', '//option', "4")
        #
        # check failing for incorrect number of xpathes
        self.sd('verifyXpathCount', '//option', "3")
        assert self.sd.getVerificationErrors() == ['Actual value "4" did not match "3"']
        self.sd.initVerificationErrors()  # reset verification messages
        
    
    def test_Select_method(self):
        """check select method and the associated find_children method (for selection lists / drop-downs)"""
        self.sd('open', '/static/form1')
        #
        # check finding option elements by given id of the select node
        self.sd('select', 'id=selectTest', "value=value1")
        #
        # check finding option elements by given xpath of the select node
        self.sd('select', '//select', "value=value2")
        #
        # check finding option elements by given name of the select node
        self.sd('select', 'name=select1', "value=value3")
        #
        # check finding option elements by given css path of the select node
        self.sd('select', 'css=#selectTest', "value=value4")
        #
        # check that all option locator parameters work as expected
        optionLocators =[('label1', '1'), ('label=label2', '2'), ('value=value3', '3'), ('id=option4', '4'), ('index=0', '1')]
        for optionLocator in optionLocators:
            self.sd('select', 'id=selectTest', optionLocator[0])
            self.sd('assertAttribute', '//select[@id="selectTest"]/option[' + optionLocator[1] + "]@selected", "true")   
        #
        # check failing using unknown option locator parameter
        with py.test.raises(UnexpectedTagNameException):
            self.sd('select', 'id=selectTest', 'xpath=//option[@id="option3"]')
        #       
        # check failing with correct option locator parameters but incorrect values    
        for optionLocator in ['label', 'label=2', 'value=value', 'id=optio4', 'index=4']:
            with py.test.raises(NoSuchElementException):
                self.sd('select', 'id=selectTest', optionLocator)
        #        
        # check failing while trying to perform a select command on a non-select element
        with py.test.raises(UnexpectedTagNameException): 
            self.sd('select', 'id=id_submit', "value=value1")

        
    def test_Check_methods(self):
        """test the uncheck and check method (for checkboxes)"""
        self.sd('open', '/static/form1')
        #
        # verify that checkbox1 is unchecked
        with py.test.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform a check command on unchecked checkbox1
        self.sd('check', '//*[@value="first"]')
        #
        # verify that checkbox1 is checked
        self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform a check command on checked checkbox1
        self.sd('check', '//*[@value="first"]')
        #
        # verify that checkbox1 is (still) checked
        self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform an uncheck command on checked checkbox1
        self.sd('uncheck', '//*[@value="first"]')
        #
        # verify that checkbox1 is unchecked
        with py.test.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform an uncheck command on unchecked checkbox1
        self.sd('uncheck', '//*[@value="first"]')
        #
        # verify that checkbox1 is (still) unchecked
        with py.test.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
            
            
    def test_Mouse_methods(self):
        """check the mouseOver and mouseOut methods"""
        self.sd('open', '/static/form1')
        #
        # check that checkbox1 is unchecked
        with py.test.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # hover the mouse over checkbox1
        self.sd('mouseOver', '//*[@name="checkbox1"]')
        #
        # click on the current position
        ActionChains(self.driver).click().perform()     
        #
        # verify that checkbox1 is checked now
        self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # move the mouse away from checkbox1
        self.sd('mouseOut', '//*[@name="checkbox1"]')   
        #
        # click on the current position
        ActionChains(self.driver).click().perform()
        #
        # verify that checkbox1 is (still) checked
        self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        
        
    def test_Aliases(self):
        """In the IDE there are aliases for "Not" commands which were generated automatically from commands with prefix "is_" 
        (most likely to increase readability). We do the same."""
        self.sd('open', '/static/page1')
        self.sd('verifyTextNotPresent', 'H1 texts')
        self.sd('assertElementNotPresent', 'id=select')
        self.sd('waitForTextNotPresent', 'H1 texts')
        
        
    def test_PopUp_methods(self):
        """check the waitForPopUp and selectWindow methods"""
        self.sd('open', '/static/page1')
        #
        # open a pop up by clicking on a link
        self.sd('click', 'link=Test popup')
        #
        # check waiting for the pop up with standard timeout
        self.sd('waitForPopUp', "stekie")
        #
        # check that the focus is still on the main window.
        assert self.sd('getText', 'css=h1') == 'H1 text'
        #
        # check waiting for a non-existent pop up with specified timeout = 2.1s
        with py.test.raises(NoSuchWindowException):
            self.sd('waitForPopUp', "no pop up", "1100")
        #
        # check failing when selecting "null" as target (not implemented yet)
        with py.test.raises(NotImplementedError):    
            self.sd('waitForPopUp', "null")
        #
        # switch focus to the pop up
        self.sd('selectWindow', "name=stekie")
        #
        # check that text in the pop up can be found.
        assert self.sd('isTextPresent', 'This is a pop up')
        #
        # switch focus back to the main window
        self.sd('selectWindow', "null")
        assert self.sd('getText', 'css=h1') == 'H1 text'
        self.sd('assertNotTextPresent', 'This is a pop up')
        #
        # check failing when using a locator parameter which is not implemented yet
        with py.test.raises(NotImplementedError):
            self.sd('selectWindow', "title=stekie")
    
            
    def test_ElementPresent_method(self):
        self.sd('open', '/static/page1')
        """check the elementPresent method"""
        #
        # check that an element can be found
        self.sd('verifyElementPresent', '//div[@class="class1"]')
        assert self.sd.getVerificationErrors() == []
        #
        # check that a missing element adds a verification error
        self.sd('verifyElementPresent', '//div[@class="class"]')
        assert self.sd.getVerificationErrors() == ['false']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # check that an element which should not be present adds a verification error
        self.sd('verifyNotElementPresent', '//div[@class="class1"]')
        assert self.sd.getVerificationErrors() == ['true']
        self.sd.initVerificationErrors()  # reset verification messages              
        #
        # check that a missing element raises an assertion error and not a NoSuchElementException (it is caught in the method)
        with py.test.raises(AssertionError):
            self.sd('assertElementPresent', '//div[@class="class"]')
        #
        # check the storing of the result of the ElementPresent method
        self.sd('storeElementPresent', '//div[@class="class"]', 'elementPresent')
        assert self.sd.storedVariables['elementPresent'] == False  
        
    def test_SeleniumStringPatterns(self):
        """testing string match parameters regexp, exact and glob in _match and _isContained methods"""
        self.sd('open', '/static/page1')
        self.sd('getText', 'css=h1', 'regexp:H1 text')
        #
        # method: _match / parameter: regexp
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'regexp:H1 tex')
        self.sd('assertText', 'css=h1', 'regexp:H1 text')
        self.sd('assertText', 'css=h1', 'regexp:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'regexp:H1*text')
        #
        # method: _match / parameter: exact
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'ecact:H1 tex')
        self.sd('assertText', 'css=h1', 'exact:H1 text')
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'exact:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'exact:H1*text')
        #
        # method: _match / parameter: glob
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'glob:H1 tex')
        self.sd('assertText', 'css=h1', 'glob:H1 text')
        with py.test.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'glob:H.* tex\w+')
        self.sd('assertText', 'css=h1', 'glob:H1*text')
        #
        # method: _isContained / parameter: regexp
        self.sd('assertTextPresent', 'regexp:H1 tex')
        self.sd('assertTextPresent', 'regexp:H1 text')
        self.sd('assertTextPresent', 'regexp:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.sd('assertTextPresent', 'regexp:H1*text')
        #
        # method: _isContained / parameter: exact
        self.sd('assertTextPresent', 'exact:H1 tex')
        self.sd('assertTextPresent', 'exact:H1 text')
        with py.test.raises(AssertionError):
            self.sd('assertTextPresent', 'exact:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.sd('assertTextPresent', 'exact:H1*text')
        #
        # method: _isContained / parameter: glob
        self.sd('assertTextPresent', 'glob:H1 tex')
        self.sd('assertTextPresent', 'glob:H1 text')
        with py.test.raises(AssertionError):
            self.sd('assertTextPresent', 'glob:H.* tex\w+')
        self.sd('assertTextPresent', 'glob:H1*text')
        
        
    def test_missing_and_unknown_locator_parameter(self):
        self.sd('open', '/static/form1')
        #
        # check that a missing locator parameter is resolved to name
        self.sd("assertElementPresent" , "text1")
        #
        # check that a missing locator parameter is resolved to id
        self.sd("assertElementPresent" , "id_text1")
        #
        # check that an unknown parameter raises an Unexpected TagNameException
        with py.test.raises(UnexpectedTagNameException):
            self.sd("assertElementPresent" , "value=first") 
            
            
    def test_SelectFrame_method(self):
        ''' testing the selectFrame method'''
        self.sd('open', '/static/page2')
        #
        # check that text in iframe1 cannot be found
        self.sd("assertTextNotPresent", "This is a text inside the first iframe")
        #
        # select iframe1
        self.sd("selectFrame", "id=iframe1")
        #
        # check that the text in iframe1 can be found
        self.sd("assertTextPresent", "This is a text inside the first iframe")
        #
        # select iframe3 (nested in iframe1)
        self.sd("selectFrame", "id=iframe3")
        #
        # check that the text in iframe3 can be found
        self.sd("assertTextPresent", "This is a text inside the third iframe")
        #
        # check the relative parameter: parent selection is not implemented yet
        with py.test.raises(NotImplementedError):
            self.sd("selectFrame", "relative=parent")
        #
        # check the relative parameter: select the top frame
        self.sd("selectFrame", "relative=top")
        #
        # check that a text in the top frame can be found
        self.sd("assertTextPresent", "Default content")
        #
        # select iframe2 by index
        self.sd("selectFrame", "1")
        #
        # check that the text in iframe2 can be found
        self.sd("assertTextPresent", "This is a text inside the second iframe")
        #
        # check that unknown relative parameter raises a NoSuchFrameException
        with py.test.raises(NoSuchFrameException):
            self.sd("selectFrame", "relative=child")
        
        
    def test_Value_and_Attribute_method(self):
        ''' testing the value and attribute method'''
        self.sd('open', '/static/form1')
        #
        # check that the value of the 'value' attribute can be found and is correct
        self.sd('assertValue', 'id=id_text1', 'input_text1')
        #
        # check that a wrong value adds a verification error
        self.sd('verifyValue', 'id=id_text1', '')
        assert self.sd.getVerificationErrors() == ['Actual value "input_text1" did not match ""']
        self.sd.initVerificationErrors()  # reset verification messages  
        #
        # check that the value of the 'type' attribute can be found and is correct
        self.sd('assertAttribute', 'id=id_submit@type', 'submit')
        #
        # check that a wrong value adds a verification error
        self.sd('verifyAttribute', 'id=id_submit@type', 'submits')
        assert self.sd.getVerificationErrors() == ['Actual value "submit" did not match "submits"']
        self.sd.initVerificationErrors()  # reset verification messages  
    
    
    def test_Type_method(self):
        ''' testing the type method'''
        self.sd('open', '/static/form1')
        #
        # type a string into an empty text field
        self.sd('type', 'id=id_text1', 'a new text')
        #
        # assert that the text field's value attribute was filled correctly
        assert self.sd('getAttribute', 'id=id_text1@value') == 'a new text'
        
    def test_Table_method(self):
        ''' testing the table method'''
        self.sd('open', '/static/page3')
        #
        # searching in a table with only a tbody element
        self.sd('assertTable', 'css=table#firstTable.2.2', 'Manchester')
        #
        # searching in a table with thead and tbody elements. The order of these elements in the html code 
        # does not correspond to the displayed order and thus the search address.
        self.sd('assertTable', 'css=table#secondTable.2.2', 'Manchester')
        #
        # searching in a table with thead, tbody and tfoot elements. The order of these elements in the 
        # html code does not correspond to the displayed order and thus the search address.
        self.sd('assertTable', 'css=table#thirdTable.2.2', 'London')

        
    def test_Command_NotImplementedError(self):
        ''' checking that a non-existent command raises a NotImplementedError'''
        with py.test.raises(NotImplementedError):
            self.sd('myNewCommand', 'action')
        
