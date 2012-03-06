"""
UT module to test webdriver commands
"""
import sys, py.test
sys.path.insert(0, '..')
###
from selenium import webdriver
from selexe.selenium_driver import SeleniumDriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchWindowException
###
# the fololowing imports provide a setup function to fire up and shutddown the (bottle) testserver!
from test_execute_sel_files import setup_module, teardown_module

BASE_URI = 'http://localhost:8080'



class Test_SeleniumDriver(object):
    def setup_method(self, method):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.wdc = SeleniumDriver(self.driver, BASE_URI)

    def teardown_method(self, method):
        self.driver.quit()

    def test_all_Text_methods(self):
        """check getText / verifyText / assertText / storeText / ... methods"""
        self.wdc('open', '/static/page1')
        #
        assert self.wdc('getText', 'css=h1') == 'H1 text'
        #
        self.wdc('verifyText', 'css=h1', 'H1 text')
        assert self.wdc.getVerificationErrors() == []
        #
        # check failing verfiyText command:
        self.wdc('verifyText', 'css=h1', 'H1 WROOOOOONG text')
        assert self.wdc.getVerificationErrors() == ['Actual value "H1 text" did not match "H1 WROOOOOONG text"']
        self.wdc.initVerificationErrors()  # reset verification messages
        #
        # check failing verfiyNotText command:
        self.wdc('verifyNotText', 'css=h1', 'H1 text')
        assert self.wdc.getVerificationErrors() == ['Actual value "H1 text" did match "H1 text"']
        self.wdc.initVerificationErrors()  # reset verification messages
        #
        self.wdc('assertText', 'css=h1', 'H1 text')
        #
        # check that wrong text raises AssertionError
        with py.test.raises(AssertionError):
            self.wdc('assertText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that correct text raises AssertionError for 'assertNotText'
        with py.test.raises(AssertionError):
            self.wdc('assertNotText', 'css=h1', 'H1 text')
        #
        self.wdc('storeText', 'css=h1', 'h1-content')
        assert self.wdc.storedVariables['h1-content'] == 'H1 text'
        #
        self.wdc('waitForText', 'css=h1', 'H1 text')
        #
        # check that waiting for non-existing text finally raises RuntimeError (after timeout):
        with py.test.raises(RuntimeError):
            self.wdc('waitForText', 'css=h1', 'H1 WROOOOOONG text', timeout=1)
        #
        # check that waiting for existing text with 'waitForNotText' raises RuntimeError (after timeout)
        with py.test.raises(RuntimeError):
            self.wdc('waitForNotText', 'css=h1', 'H1 text', timeout=1)
            
    
    def test_Alert_methods(self):
        """check alert methods"""
        # testing alert method after clicking on a button which opens an alert window
        self.wdc('open', '/static/page1')
        self.wdc('click', '//input[@type="button"]')
        self.wdc('assertAlert', 'hello')
        #
        # checking that a wrong text adds a verification error
        self.wdc('click', '//input[@type="button"]')
        self.wdc('verifyAlert', 'a wrong text')
        assert self.wdc.getVerificationErrors() == ['Actual value "hello" did not match "a wrong text"']
        self.wdc.initVerificationErrors()  # reset verification messages
        #
        # checking that a missing alert raises an exception
        with py.test.raises(NoAlertPresentException):
            self.wdc('assertAlert', 'hello')
        #
        # checking that a missing alert raises an exception but is caught in the verify wrapper    
        self.wdc('verifyAlert', 'hello')
        assert self.wdc.getVerificationErrors() == ['There were no alerts or confirmations']
        self.wdc.initVerificationErrors()  # reset verification messages
         # checking that a missing alert raises an exception but is caught in the verifyNot wrapper    
        self.wdc('verifyNotAlert', 'hello')
        assert self.wdc.getVerificationErrors() == ['There were no alerts or confirmations']
        self.wdc.initVerificationErrors()  # reset verification messages
        #
        # testing the confirmation method which is just an alias for the alert method
        self.wdc('click', '//input[@type="button"]')
        self.wdc('storeConfirmation', 'confirmationMessagePresent')
        
            
    def test_XpathCount_method(self):
        """check XpathCount method and the associated find_targets method"""
        self.wdc('open', '/static/form1')
        # note: this method returns two integers (instead of strings or booleans like all the other return methods)
        self.wdc('assertXpathCount', '//option', "4")
        #
        # check failing for incorrect number of xpathes
        self.wdc('verifyXpathCount', '//option', "3")
        assert self.wdc.getVerificationErrors() == ['Actual value "4" did not match "3"']
        self.wdc.initVerificationErrors()  # reset verification messages
        
    
    def test_Select_method(self):
        """check select method and the associated find_children method"""
        self.wdc('open', '/static/form1')
        #
        # test all option locators
        for optionLocator in ['label1', 'label=label2', 'value=value3', 'id=option4', 'index=1']:
            self.wdc('select', 'id=selectTest', optionLocator)
        #       
        # test that select fails with false values for option locators     
        for optionLocator in ['label', 'label=2', 'value=value', 'id=optio4', 'index=4']:
            with py.test.raises(NoSuchElementException):
                self.wdc('select', 'id=selectTest', optionLocator)
        #
        # unknown option locator
        with py.test.raises(RuntimeError):
            self.wdc('select', 'id=selectTest', "xpath=sss")
        #    
        # test find_children method
        #
        # find children by id
        self.wdc('select', 'id=selectTest', "value=value1")
        #
        # find children by xpath
        self.wdc('select', '//select', "value=value2")
        #
        # find children by name
        self.wdc('select', 'select1', "value=value3")
        #
        # find children by css
        self.wdc('select', 'css=#selectTest', "value=value4")
        #
        # unknown option locator
        with py.test.raises(RuntimeError):
            self.wdc('select', 'value=selectTest', "value=value1")
        
    def test_Check_methods(self):
        '''test the uncheck and check method'''
        self.wdc('open', '/static/form1')
        #
        # testing the check method
        self.wdc('check', '//*[@value="first"]')
        #
        # testing the check method on a checked checkbox
        self.wdc('check', '//*[@value="first"]')
        #
        # testing the uncheck method
        self.wdc('uncheck', '//*[@value="first"]')
        #
        # testing the uncheck method on a unchecked checkbox
        self.wdc('uncheck', '//*[@value="first"]')
        
    def test_Aliases(self):
        ''' Aliases redirect to methods which were generated by the decorater method. In the IDE there are for some methods 
        two "Not" methods, which are duplicates in content'''
        self.wdc('open', '/static/page1')
        self.wdc('verifyTextNotPresent', 'H1 texts')
        self.wdc('assertTextNotPresent', 'H1 texts')
        self.wdc('waitForTextNotPresent', 'H1 texts')
        self.wdc('verifyElementNotPresent', 'id=select')
        self.wdc('assertElementNotPresent', 'id=select')
        self.wdc('waitForElementNotPresent', 'id=select')
        
    def test_PopUp_methods(self):
        '''test the waitForPopUp and selectWindow methods'''
        self.wdc('open', '/static/page1')
        #
        # open the pop up by clicking on a link
        self.wdc('click', 'link=Test popup')
        #
        # now waiting for the pop up with standard timeout
        self.wdc('waitForPopUp', "stekie")
        #
        # is the focus back on the main window? Check smth. on the page.
        assert self.wdc('getText', 'css=h1') == 'H1 text'
        #
        # waiting for a non-existant pop up with specified timeout = 2s which results in two pollings
        with py.test.raises(NoSuchWindowException):
            self.wdc('waitForPopUp', "no pop up", "2000")
        #
        # selecting "null" as target which is not implemented yet
        with py.test.raises(NotImplementedError):    
            self.wdc('waitForPopUp', "null")
        #
        # now switch focus the pop up
        self.wdc('selectWindow', "name=stekie")
        assert self.wdc('getTextPresent', 'This is a pop up')
        #
        # now switch focus back to the main window
        self.wdc('selectWindow', "null")
        assert self.wdc('getText', 'css=h1') == 'H1 text'
        self.wdc('assertNotTextPresent', 'This is a pop up')
        #
        # using a window locator which is not implemented yet
        with py.test.raises(NotImplementedError):
            self.wdc('selectWindow', "title=stekie")
    
            
    def test_ElementPresent_method(self):
        self.wdc('open', '/static/page1')
        '''testint elementPresent method'''
        #
        # element can be found
        self.wdc('verifyElementPresent', '//p[@class="class1"]')
        assert self.wdc.getVerificationErrors() == []
        #
        # element can not be found
        self.wdc('verifyElementPresent', '//p[@class="class"]')
        assert self.wdc.getVerificationErrors() == ['false']
        self.wdc.initVerificationErrors()  # reset verification messages
        #
        # element can be found but should not be found
        self.wdc('verifyNotElementPresent', '//p[@class="class1"]')
        assert self.wdc.getVerificationErrors() == ['true']
        self.wdc.initVerificationErrors()  # reset verification messages              
        #
        # element can not be found (assert should catch NoSuchElementException)
        with py.test.raises(AssertionError):
            self.wdc('assertElementPresent', '//p[@class="class"]')
        
    def test_SeleniumStringPatterns(self):
        '''testing string match parameters regexp:, exact: and glob: in match and isContained methods'''
        self.wdc('open', '/static/page1')
        #
        # match - regexp:
        self.wdc('assertText', 'css=h1', 'regexp:H1 text')
        self.wdc('assertText', 'css=h1', 'regexp:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.wdc('assertText', 'css=h1', 'regexp:H1*text')
        #
        # match - exact:
        self.wdc('assertText', 'css=h1', 'exact:H1 text')
        with py.test.raises(AssertionError):
            self.wdc('assertText', 'css=h1', 'exact:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.wdc('assertText', 'css=h1', 'exact:H1*text')
        #
        # match - glob:
        self.wdc('assertText', 'css=h1', 'glob:H1 text')
        with py.test.raises(AssertionError):
            self.wdc('assertText', 'css=h1', 'glob:H.* tex\w+')
        self.wdc('assertText', 'css=h1', 'glob:H1*text')
        #
        # isContained - regexp:
        self.wdc('assertTextPresent', 'regexp:H1 tex')
        self.wdc('assertTextPresent', 'regexp:H1 text')
        self.wdc('assertTextPresent', 'regexp:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.wdc('assertTextPresent', 'regexp:H1*text')
        #
        # isContained - exact:
        self.wdc('assertTextPresent', 'exact:H1 tex')
        self.wdc('assertTextPresent', 'exact:H1 text')
        with py.test.raises(AssertionError):
            self.wdc('assertTextPresent', 'exact:H.* tex\w+')
        with py.test.raises(AssertionError):
            self.wdc('assertTextPresent', 'exact:H1*text')
        #
        # isContained - glob:
        self.wdc('assertTextPresent', 'glob:H1 tex')
        self.wdc('assertTextPresent', 'glob:H1 text')
        with py.test.raises(AssertionError):
            self.wdc('assertTextPresent', 'glob:H.* tex\w+')
        self.wdc('assertTextPresent', 'glob:H1*text')
        