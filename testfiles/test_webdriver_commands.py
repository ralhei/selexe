"""
UT module to test webdriver commands
"""
import sys
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

    def test_verifyText(self):
        self.wdc('open', '/static/page1')
        assert self.wdc('getText', 'css=h1') == 'H1 text'
        self.wdc('verifyText', 'css=h1', 'H1 text')
