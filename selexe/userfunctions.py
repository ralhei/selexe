'''
Created on 26.02.2012

@author: Stephan Kienzle
'''
import httplib
#from webdriver_commands import find_children, find_target, find_targets, matches, isContained, _tag_and_value

class Userfunctions(object):
           
    def __init__(self, driver):
        self.driver = driver
        self.base_url = driver.base_url
        if "http://" in self.base_url:
            self.base_url = self.base_url[7:] 
           
    '''
    Selenium.prototype.doPutRest = function(url, data) {
        var jQuery = this.browserbot.getUserWindow().jQuery;
        jQuery.ajax({url: url, data: data, processData: false, 
            contentType: 'application/json', async: false, type: 'put'});
    };
    '''          
    def wd_putRest(self, target, value):
        connection =  httplib.HTTPConnection(self.base_url)
        connection.request('PUT', target , value)
        result = connection.getresponse()
    '''
    Selenium.prototype.doDeleteRest = function(url) {
        this.browserbot.getUserWindow().jQuery.ajax({url: url, async: false,
        type: 'delete'});
    };
    '''
    def wd_deleteRest(self, target, value):
        pass
        
    '''  
    Selenium.prototype.assertGetRest = function(url, data) {
    var actualData = this.browserbot.getUserWindow().jQuery.ajax({url: url,
        async: false, type: 'get'}).responseText;
    var expectedData = this.browserbot.getUserWindow().jQuery.parsJSON(data);
    var actualData = this.browserbot.getUserWindow().jQuery.parseJSON(actualData);
    for (var key in expectedData) {
        if ( expectedData[key] != actualData[key]) {
            throw new SeleniumError (key + ": actual value " + actualValue + 
                    " does not match expected value " + expectedValue);
            };
        };
    };    
    '''
    def wd_assertGetRest(self, target, value):
        pass
        
    '''
    Selenium.prototype.getTextLength = function(locator) {
        var length = thisgetText(locator).length;
        return length;
    };
    '''
   
    def wd_getTextLength(self, target, value):
        pass
    
    '''
    Selenium.prototype.assertTextContainedInEachElement = function(locator, text) {
        var doc = this.browserbot.getCurrentWindow().document;
        var elements = doc.evalutate(locator, doc, null, XPathResult.ANY_TYPE, null);
        var element = elements.iterateNext();
        while (element) {
            Assert.matches("true", element.textContent.indexOf(text) != -1);
            element = elements.iterateNext();
        };
    };
    '''
   
    def wd_assertTextContainedInEachElement(self, target, value):
        pass
    
    '''
    Selenium.prototype.doVerifyValidation = function(locator, expectedStatus) {
        try {
            numOfLoops++;
            //alert(numOfLoops);
            var expectedStatusArray = expectedStatus.split(":");
            var expectedAttributeValue = this.browserbot.getCurrentWindow().jQuery.
            trim(expectedStatusArray[0]);
            var expectedValidationMsg = this.browserbot.getCurrentWindow().jQuery.
            trim(expectedStatusArray[1]);
            var actualAttributeValue = this.getAttribute(locator + '@class');
            
            if (actualAttributeValue != expectedAttributeValue && numOfLoops <
                    MAXNUMOFLOOPS) {
                NotWaitingForCondition = function() {
                    return selenium.doVerifyValidation(locator, expectedStatus);
                };
            } else if (actualAttributeValue == expectedAttributeValue) {
                resetWaitParams();
                this.doMouseOver(locator);
                actualValidationMsg = this.getText('id=validationMsg');
                Assert.matches(actualValidationMsg, expectedValidationMsg);
                this.doMouseOut(locator);
            } else {
                resetWaitParams();
                Assert.matches(actualAttributeValue, expectedAttributeValue);
            };
        return false;
        // Errors are catched because selenium will be corrupted otherwise. The wait
        //    parameters have to be reseted.
        } catch (e) {
            resetWaitParams();
            throw new SeleniumError(e);
        };
    };

    function ActionResult(terminationCondition) {
        this.terminationCondition = function() {
            //alert ("Hallo");
            //alert (!NotWaitingForCondition);
            return true;
            //return terminationCondition; //&& NotWaitingForCondition();
        };
    };
    
    
    function NotWaitingForCondition() {
        return true;
    };
    
    var numOfLoops = 0;
    var MAXNUMOFLOOPS = 5;
    
    function resetWaitParams() {
        numOfLoops = 0;
        NotWaitingForCondition = function() {
            return true;
        };
    };
    '''
    def wd_doVerifyValidation(self, target, value):
        pass
    