"""
UT module to test selenium-driver commands
"""
import sys, pytest, time
sys.path.insert(0, '..')
###
from selenium import webdriver
from selexe.selenium_driver import SeleniumDriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import UnexpectedTagNameException
from selenium.common.exceptions import NoSuchFrameException
from selenium.common.exceptions import NoSuchAttributeException
from selenium.webdriver.common.action_chains import ActionChains

###
# the fololowing imports provide a setup function to fire up and shutddown the (bottle) testserver!
from test_execute_sel_files import setup_module, teardown_module

BASE_URI = 'http://localhost:8080'



class Test_SeleniumDriver(object):
    def setup_method(self, method):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.sd = SeleniumDriver(self.driver, BASE_URI)

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
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that correct text raises AssertionError for 'assertNotText'
        with pytest.raises(AssertionError):
            self.sd('assertNotText', 'css=h1', 'H1 text')
        #
        self.sd('storeText', 'css=h1', 'h1content')
        assert self.sd.storedVariables['h1content'] == 'H1 text'
        self.sd('assertText', 'css=h1', '${h1content}')
        #
        # check that a NoSuchElmenentException is not caught
        with pytest.raises(NoSuchElementException):
            self.sd('verifyText', '//p[@class="class"]')  
        #
        self.sd('waitForText', 'css=h1', 'H1 text')
        #
        # text is inserted 3000 ms after clicking on the button
        self.sd('click', 'id=textInsertDelay')
        self.sd('waitForTextPresent', 'Text was inserted')
        #
        # text is deleted 3000 ms after clicking on the button
        self.sd('click', 'id=textRemoveDelay')
        self.sd('waitForNotTextPresent', 'Text was inserted')
        #
        # check that waiting for non-existing text finally raises RuntimeError (after timeout):
        with pytest.raises(RuntimeError):
            self.sd('waitForText', 'css=h1', 'H1 WROOOOOONG text', timeout=1000)
        #
        # check that waiting for existing text with 'waitForNotText' raises RuntimeError (after timeout)
        with pytest.raises(RuntimeError):
            self.sd('waitForNotText', 'css=h1', 'H1 text', timeout=1000)
             
    
    def test_Alert_methods(self):
        """check alert methods"""
        # checking that an alert is found
        self.sd('open', '/static/page1')
        self.sd('clickAndWait', '//input[@type="button" and @value="alert button"]')
        self.sd('assertAlert', 'hello')
        #
        # check that a wrong alert text adds a verification error
        self.sd('click', '//input[@value="alert button"]')
        self.sd('verifyAlert', 'a wrong text')
        assert self.sd.getVerificationErrors() == ['Actual value "hello" did not match "a wrong text"']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # check that a missing alert raises an exception
        with pytest.raises(NoAlertPresentException):
            self.sd('assertAlert', 'hello')
        #
        # check that a missing alert adds a verification error    
        self.sd('verifyAlert', 'hello')
        assert self.sd.getVerificationErrors() == ['There were no alerts or confirmations']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # check that a missing alert adds a verification error (added by verifyNot Wrapper)   
        self.sd('verifyNotAlert', 'hello')
        assert self.sd.getVerificationErrors() == ['There were no alerts or confirmations']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # checks the confirmation method which is an alias for the alert method
        # stores it
        self.sd('click', '//input[@value="alert button"]')
        self.sd('storeConfirmation', 'confirmationMsg')
        assert self.sd.storedVariables['confirmationMsg'] == 'hello'
        
            
    def test_XpathCount_method(self):
        """check the XpathCount method and the associated find_targets method"""
        self.sd('open', '/static/form1')
        # note: this method returns two integers (instead of strings or booleans like all the other return methods)
        self.sd('assertXpathCount', '//option', "4")
        #
        # check failing for incorrect number of xpathes
        self.sd('verifyXpathCount', '//option', "3")
        assert self.sd.getVerificationErrors() == ['Actual value "4" did not match "3"']
        self.sd.initVerificationErrors()  # reset verification messages
        
    
    def test_Select_method(self):
        """check the select method and the associated _find_children method"""
        self.sd('open', '/static/form1')
        #
        # test all option locators
        for optionLocator in ['label1', 'label=label2', 'value=value3', 'id=option4', 'index=1']:
            self.sd('select', 'id=selectTest', optionLocator)
        #
        # unknown option locator
        with pytest.raises(RuntimeError):
            self.sd('select', 'id=selectTest', 'xpath=//option[@id="option3"]')
        #       
        # test that select fails with false values for option locators     
        for optionLocator in ['label', 'label=2', 'value=value', 'id=optio4', 'index=4']:
            with pytest.raises(NoSuchElementException):
                self.sd('select', 'id=selectTest', optionLocator)
        #        
        # no select Element
        with pytest.raises(UnexpectedTagNameException): 
            self.sd('select', 'id=id_submit', "value=value1")
        #    
        # test find_children method
        #
        # find children by id
        self.sd('select', 'id=selectTest', "value=value1")
        #
        # find children by xpath
        self.sd('select', '//select', "value=value2")
        #
        # find children by name
        self.sd('select', 'name=select1', "value=value3")
        #
        # find children by css
        self.sd('select', 'css=#selectTest', "value=value4")

        
    def test_Check_methods(self):
        """check the uncheck and check methods"""
        self.sd('open', '/static/form1')
        #
        # verify that checkbox1 is unchecked
        with pytest.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform a check command on an unchecked checkbox
        self.sd('check', '//*[@value="first"]')
        #
        # verify that checkbox1 is checked
        self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform a check command on a checked checkbox
        self.sd('check', '//*[@value="first"]')
        #
        # verify that checkbox1 is (still) checked
        self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform an uncheck command on an checked checkbox
        self.sd('uncheck', '//*[@value="first"]')
        #
        # verify that checkbox1 is unchecked
        with pytest.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # perform an uncheck command on a unchecked checkbox
        self.sd('uncheck', '//*[@value="first"]')
        #
        # verify that checkbox1 is (still) unchecked
        with pytest.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
            
            
    def test_Mouse_methods(self):
        """check the mouseOver and mouseOut methods"""
        self.sd('open', '/static/form1')
        #
        # check that checkbox1 is unchecked
        with pytest.raises(NoSuchAttributeException):
            self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        #
        # hover the mouse over the checkbox1
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
        # do an uncheck command on a unchecked checkbox 
        self.sd('assertAttribute', '//*[@name="checkbox1"]@checked', 'true')
        
        
    def test_Aliases(self):
        """ In the IDE there are aliases for "Not" commands which were generated automatically from commands with prefix "is_" 
        (most likely to increase readability). Currently theses aliases are added manually to our code"""
        self.sd('open', '/static/page1')
        self.sd('verifyTextNotPresent', 'H1 texts')
        self.sd('assertTextNotPresent', 'H1 texts')
        self.sd('waitForTextNotPresent', 'H1 texts')
        self.sd('verifyElementNotPresent', 'id=select')
        self.sd('assertElementNotPresent', 'id=select')
        self.sd('waitForElementNotPresent', 'id=select')
        
        
    def test_PopUp_methods(self):
        """check the waitForPopUp and selectWindow methods"""
        self.sd('open', '/static/page1')
        #
        # open the pop up by clicking on a link
        self.sd('click', 'link=Test popup')
        #
        # now waiting for the pop up with standard timeout
        self.sd('waitForPopUp', "stekie")
        #
        # is the focus back on the main window? Check smth. on the page.
        assert self.sd('getText', 'css=h1') == 'H1 text'
        #
        # waiting for a non-existant pop up with specified timeout = 2.1s which results in two pollings
        with pytest.raises(NoSuchWindowException):
            self.sd('waitForPopUp', "no pop up", "2100")
        #
        # selecting "null" as target which is not implemented yet
        with pytest.raises(NotImplementedError):    
            self.sd('waitForPopUp', "null")
        #
        # now switch focus the pop up
        self.sd('selectWindow', "name=stekie")
        assert self.sd('isTextPresent', 'This is a pop up')
        #
        # now switch focus back to the main window
        self.sd('selectWindow', "null")
        assert self.sd('getText', 'css=h1') == 'H1 text'
        self.sd('assertNotTextPresent', 'This is a pop up')
        #
        # using a window locator which is not implemented yet
        with pytest.raises(NotImplementedError):
            self.sd('selectWindow', "title=stekie")
    
            
    def test_ElementPresent_method(self):
        self.sd('open', '/static/page1')
        """check the elementPresent method"""
        #
        # check that element can be found
        self.sd('verifyElementPresent', '//div[@class="class1"]')
        assert self.sd.getVerificationErrors() == []
        #
        # element can not be found. Check that the verify wrapper produces the expectant error
        self.sd('verifyElementPresent', '//div[@class="class"]')
        assert self.sd.getVerificationErrors() == ['false']
        self.sd.initVerificationErrors()  # reset verification messages
        #
        # element can be found but should not be found. Check that the verify wrapper produces the expectant error
        self.sd('verifyNotElementPresent', '//div[@class="class1"]')
        assert self.sd.getVerificationErrors() == ['true']
        self.sd.initVerificationErrors()  # reset verification messages              
        #
        # element can not be found. Check that method catches a NoSuchElementException)
        with pytest.raises(AssertionError):
            self.sd('assertElementPresent', '//div[@class="class"]')
        #
        # stores element present == false
        self.sd('storeElementPresent', '//div[@class="class"]', 'elementPresent')
        assert self.sd.storedVariables['elementPresent'] == 'false'
            
        
    def test_SeleniumStringPatterns(self):
        """testing string match parameters regexp:, exact: and glob: in _match and _isContained methods"""
        self.sd('open', '/static/page1')
        self.sd('getText', 'css=h1', 'regexp:H1 text')
        #
        # match - regexp:
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'regexp:H1 tex')
        self.sd('assertText', 'css=h1', 'regexp:H1 text')
        self.sd('assertText', 'css=h1', 'regexp:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'regexp:H1*text')
        #
        # match - exact:
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'ecact:H1 tex')
        self.sd('assertText', 'css=h1', 'exact:H1 text')
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'exact:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'exact:H1*text')
        #
        # match - glob:
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'glob:H1 tex')
        self.sd('assertText', 'css=h1', 'glob:H1 text')
        with pytest.raises(AssertionError):
            self.sd('assertText', 'css=h1', 'glob:H.* tex\w+')
        self.sd('assertText', 'css=h1', 'glob:H1*text')
        #
        # isContained - regexp:
        self.sd('assertTextPresent', 'regexp:H1 tex')
        self.sd('assertTextPresent', 'regexp:H1 text')
        self.sd('assertTextPresent', 'regexp:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.sd('assertTextPresent', 'regexp:H1*text')
        #
        # isContained - exact:
        self.sd('assertTextPresent', 'exact:H1 tex')
        self.sd('assertTextPresent', 'exact:H1 text')
        with pytest.raises(AssertionError):
            self.sd('assertTextPresent', 'exact:H.* tex\w+')
        with pytest.raises(AssertionError):
            self.sd('assertTextPresent', 'exact:H1*text')
        #
        # isContained - glob:
        self.sd('assertTextPresent', 'glob:H1 tex')
        self.sd('assertTextPresent', 'glob:H1 text')
        with pytest.raises(AssertionError):
            self.sd('assertTextPresent', 'glob:H.* tex\w+')
        self.sd('assertTextPresent', 'glob:H1*text')
        
        
    def test_missing_and_wrong_locator_type(self):
        self.sd('open', '/static/form1')
        #
        # missing locator type: should be resolved to name
        self.sd("assertElementPresent" , "text1")
        #
        # missing locator type: should be resolved to id
        self.sd("assertElementPresent" , "id_text1")
        #
        # wrong locator type should raise an Unexpected TagNameException
        with pytest.raises(UnexpectedTagNameException):
            self.sd("assertElementPresent" , "value=first") 
            
            
    def test_SelectFrame_method(self):
        ''' testing the selectFrame method'''
        self.sd('open', '/static/page2')
        #
        # check that text in the first iframe cannot be found
        self.sd("assertTextNotPresent", "This is a text inside the first iframe")
        #
        # select iframe1
        self.sd("selectFrame", "id=iframe1")
        #
        # check that the text in the selected iframe can be found
        self.sd("assertTextPresent", "This is a text inside the first iframe")
        #
        # select iframe3 (nested in iframe1)
        self.sd("selectFrame", "id=iframe3")
        #
        # check that the text in the selected iframe can be found
        self.sd("assertTextPresent", "This is a text inside the third iframe")
        #
        # using the relative option: parent selection is not implemented yet
        with pytest.raises(NotImplementedError):
            self.sd("selectFrame", "relative=parent")
        #
        # using the relative option: select the top frame
        self.sd("selectFrame", "relative=top")
        #
        # check that text in the top frame can be found
        self.sd("assertTextPresent", "Default content")
        #
        # select iframe2 by index
        self.sd("selectFrame", "1")
        #
        # check that the text in the selected iframe can be found
        self.sd("assertTextPresent", "This is a text inside the second iframe")
        #
        # unknown selector for relative option raises a NoSuchFrameException
        with pytest.raises(NoSuchFrameException):
            self.sd("selectFrame", "relative=child")
        
        
    def test_Value_and_Attribute_method(self):
        ''' testing the value and attribute method'''
        self.sd('open', '/static/form1')
        #
        # check that the value (of value) can be found and is correct
        self.sd('assertValue', 'id=id_text1', 'input_text1')
        #
        # value is wrong. Check that the verify wrapper generates the expectant error message.
        self.sd('verifyValue', 'id=id_text1', '')
        assert self.sd.getVerificationErrors() == ['Actual value "input_text1" did not match ""']
        #
        self.sd.initVerificationErrors()  # reset verification messages  
        #
        # check that the attribute value can be found and is correct
        self.sd('assertAttribute', 'id=id_submit@type', 'submit')
        #
        # attribute value is wrong. Check that the verify wrapper generates the expectant error message.
        self.sd('verifyAttribute', 'id=id_submit@type', 'submits')
        assert self.sd.getVerificationErrors() == ['Actual value "submit" did not match "submits"']
        self.sd.initVerificationErrors()  # reset verification messages  
    
    
    def test_Type_method(self):
        ''' testing the type method'''
        self.sd('open', '/static/form1')
        self.sd('type', 'id=id_text1', 'a new text')
        self.sd('click', 'id=id_submit')
        
        
    def test_Command_NotImplementedError(self):
        ''' checking that a non-existent command raises a NotImplementedError'''
        with pytest.raises(NotImplementedError):
            self.sd('myNewCommand', 'action')
        