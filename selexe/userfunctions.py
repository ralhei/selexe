import httplib, json, time

class Userfunctions(object):
           
    def __init__(self, selenium_driver):
        self.sd = selenium_driver
        self.base_url = selenium_driver.base_url
        if self.base_url.startswith('http://'):
            self.base_url = self.base_url[7:] 
           
    def putRest(self, target, value):
        """
        Selenium.prototype.doPutRest = function(url, data) {
            var jQuery = this.browserbot.getUserWindow().jQuery;
            jQuery.ajax({url: url, data: data, processData: false, 
                contentType: 'application/json', async: false, type: 'put'});
        };
        """
        connection = httplib.HTTPConnection(self.base_url)
        headers = {"Content-type": 'application/json'}
        connection.request('PUT', target, value, headers)
        assert connection.getresponse().status == 200


    def deleteRest(self, target, value):
        """
        Selenium.prototype.doDeleteRest = function(url) {
            this.browserbot.getUserWindow().jQuery.ajax({url: url, async: false,
            type: 'delete'});
        };
        """
        connection = httplib.HTTPConnection(self.base_url)
        connection.request('DELETE', target)
        assert connection.getresponse().status == 200
        
    def assertGetRest(self, target, value):
        """  
        Selenium.prototype.assertGetRest = function(url, data) {
        var actualData = this.browserbot.getUserWindow().jQuery.ajax({url: url,
            async: false, type: 'get'}).responseText;
        var expectedData = this.browserbot.getUserWindow().jQuery.parsJSON(data);
        var actualData = this.browserbot.getUserWindow().jQuery.parseJSON(actualData);
        for (var key in expectedData) {
            if (expectedData[key] != actualData[key]) {
                throw new SeleniumError (key + ": actual value " + actualValue + 
                        " does not match expected value " + expectedValue);
                };
            };
        };    
        """
        connection = httplib.HTTPConnection(self.base_url)
        response = connection.request('GET', target).getresponse()
        assert response.status == 200
        data = json.loads(response.read())
        expectedData = json.loads(value)
        for key in expectedData:
            if data[key] != expectedData[key]:
                raise AssertionError("%s: actual value %s does not match expected value %s" \
                                     % key, str(data[key]), str(expectedData[key]))
    
   
    def assertTextContainedInEachElement(self, target, value):
        """
        Selenium.prototype.assertTextContainedInEachElement = function(locator, text) {
            var doc = this.browserbot.getCurrentWindow().document;
            var elements = doc.evalutate(locator, doc, null, XPathResult.ANY_TYPE, null);
            var element = elements.iterateNext();
            while (element) {
                Assert.matches("true", element.textContent.indexOf(text) != -1);
                element = elements.iterateNext();
            };
        };
        """
        target_elems = self.sd.driver.find_elements_by_xpath(target)
        for target_elem in target_elems:
            assert self.sd._isContained(value, target_elem.text)
    
    
    def verifyValidation(self, target, value):
        """
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
            // Errors are caught because selenium will be corrupted otherwise. The wait
            //    parameters have to be reseted.
            } catch (e) {
                resetWaitParams();
                throw new SeleniumError(e);
            };
        };
    
        function ActionResult(terminationCondition) {
            this.terminationCondition = function() {
                return true;
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
        """
        expectedClassValue, expectedValidationMsg = value.split(':') if ':' in value else value, ''
        self.sd.waitForAttribute(target + '@class', expectedClassValue.strip())
        target_elem = self.sd._find_target(target)
        self.sd.mouseOver(target_elem)
        assert self.sd.getText('id=validationMsg').strip() == expectedValidationMsg.strip()
        self.sd.mouseOut(target_elem)
    
