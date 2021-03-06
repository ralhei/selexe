import json
import http.client
from selenium.webdriver.common.action_chains import ActionChains


def _connect(url):
    url = url[7:] if url.startswith('http://') else url
    connection = http.client.HTTPConnection(url)
    return connection


def putRest(self, target, value):
    """
    Selenium.prototype.doPutRest = function(url, data) {
        var jQuery = this.browserbot.getUserWindow().jQuery;
        jQuery.ajax({url: url, data: data, processData: false,
            contentType: 'application/json', async: false, type: 'put'});
    };
    """
    connection = _connect(self.baseuri)
    headers = {"Content-type": 'application/json'}
    connection.request('PUT', target, value, headers)
    assert connection.getresponse().status == 200


def postRest(self, target, value):
    connection = _connect(self.baseuri)
    headers = {"Content-type": 'application/json'}
    connection.request('POST', target, value, headers)
    assert connection.getresponse().status == 200


def deleteRest(self, target, _value):
    """
    Selenium.prototype.doDeleteRest = function(url) {
        this.browserbot.getUserWindow().jQuery.ajax({url: url, async: false,
        type: 'delete'});
    };
    """
    connection = _connect(self.baseuri)
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
    connection = _connect(self.baseuri)
    connection.request('GET', target)
    response = connection.getresponse()
    assert response.status == 200
    # do a strip because a json value is returned in a list if it is requested with parameters
    data = json.loads(response.read().strip('[]'))
    expectedData = json.loads(value)
    for key in expectedData:
        if data[key] != expectedData[key]:
            raise AssertionError("%s: actual value %s does not match expected value %s"
                                 % key, data[key], expectedData[key])


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
    target_elems = self.driver.find_elements_by_xpath(target)
    for target_elem in target_elems:
        assert self._isContained(value, target_elem.text)


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
        //    parameters have to be reset.
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
    expected_class_value, expected_validation_msg = value.split(':') if ':' in value else [value, '']
    target_elem = self._find_target(target)
    assert expected_class_value.strip() in target_elem.get_attribute('class')
    # Move the element of interest into the viewport to make the validation message appear at all. Scroll 100 pixels
    # above the actual element to move a little bir further into the viewport:
    y = target_elem.location['y'] - 100
    self.driver.execute_script('window.scroll(0, %d)' % y)
    ActionChains(self.driver).move_by_offset(1000, 1000)
    ActionChains(self.driver).move_to_element(target_elem).perform()
    self.waitForText('id=validationMsg', expected_validation_msg.strip())


def waitForVerifyValidation(self, target, value):
    """The verify validation variant waiting for the expected error class and validation message to show up.

    Validation message are usually set as a result of a ajax request, so wait some time until the result takes effect.
    :param target:
    :param value:
    :raises AssertionError: Either when the wrong error message is displayed, or the error class did not get set.
    """
    for _ in self.retries():
        try:
            self.verifyValidation(target, value)
            break
        except AssertionError:
            continue
    else:
        # After timeout raise AssertionError:
        raise AssertionError
