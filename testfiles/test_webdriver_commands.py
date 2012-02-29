"""
UT module to test webdriver commands
"""
import sys, pytest
sys.path.insert(0, '..')
###
from selenium import webdriver
from selexe.webdriver_commands import Webdriver
###
# the fololowing imports provide a setup function to fire up and shutddown the (bottle) testserver!
from test_execute_sel_files import setup_module, teardown_module

BASE_URI = 'http://localhost:8080'



class Test_WebDriverCommands(object):
    def setup_method(self, method):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.wdc = Webdriver(self.driver, BASE_URI)

    def teardown_method(self, method):
        self.driver.quit()

    def test_all_Text_methods(self):
        """check getText / verifyText / assertText / storeText / ... methods """
        self.wdc('open', '/static/page1')
        #
        assert self.wdc('getText', 'css=h1') == 'H1 text'
        #
        self.wdc('verifyText', 'css=h1', 'H1 text')
        assert self.wdc.getVerificationErrors() == []
        #
        # check failing verfiyText command:
        self.wdc('verifyText', 'css=h1', 'H1 WROOOOOONG text')
        assert self.wdc.getVerificationErrors() == ['Value "H1 text" did not match "H1 WROOOOOONG text"']
        self.wdc.initVerificationErrors()  # reset verification messages
        #
        self.wdc('assertText', 'css=h1', 'H1 text')
        #
        # check that wrong text raises AssertionError
        with pytest.raises(AssertionError):
            self.wdc('assertText', 'css=h1', 'H1 WROOOOOONG text')
        #
        # check that correct text raises AssertionError for 'assertNotText'
        with pytest.raises(AssertionError):
            self.wdc('assertNotText', 'css=h1', 'H1 text')
        #
        self.wdc('storeText', 'css=h1', 'h1-content')
        assert self.wdc.storedVariables['h1-content'] == 'H1 text'
        #
        self.wdc('waitForText', 'css=h1', 'H1 text')
        #
        # Check that waiting for non-existing text finally raises RuntimeError (after timeout):
        with pytest.raises(RuntimeError):
            self.wdc('waitForText', 'css=h1', 'H1 WROOOOOONG text', timeout=1)
        #
        # check that waiting for existing text with 'waitForNotText' raises RuntimeError (after timeout)
        with pytest.raises(RuntimeError):
            self.wdc('waitForNotText', 'css=h1', 'H1 text', timeout=1)

