
import logging
import six

from selenium.common.exceptions import NoSuchElementException, NoAlertPresentException, StaleElementReferenceException

logger = logging.getLogger(__name__)

NOT_PRESENT_EXCEPTIONS = (NoSuchElementException, NoAlertPresentException, StaleElementReferenceException)


def selenium_multicommand_discover(klass):
    """
    Class-decorator which looks for seleniumgeneric instances in attributes and
    generate proper related selenium command methods.

    :param: klass: class that is decorated, most likely SeleniumDriver
    :returns: given class
    """
    dct = klass.__dict__
    genericattrs = [(key, value) for key, value in dct.items() if isinstance(value, SeleniumMultiCommandType)]
    relatedattrs = [(fnc.__name__, fnc) for key, value in genericattrs for fnc in value.related_commands()]

    for key, value in genericattrs:
        delattr(klass, key)
    for key, value in relatedattrs:
        setattr(klass, key, value)
    return klass


class SeleniumCommand(object):
    __slots__ = ('fnc', 'name', 'docstring', 'defaults', 'wait_for_page', '_original_name')

    @classmethod
    def nowait(cls, fnc):
        """
        Convenience alternate constructor which initializes wait_for_page attribute to false for decorator usage.

        If wait_for_page attribute is set to True, the command waits for an ongoing page load gets finished, if any,
        before running.

        @param fnc: function to be encapsulated
        @return instance of this class
        """
        obj = cls(fnc)
        obj.wait_for_page = False
        return obj

    def __init__(self, fnc):
        self.fnc = fnc
        self.name = getattr(fnc, 'fnc_name', None) or getattr(fnc, '__name__', None) \
            or getattr(fnc.__class__, '__name__')
        self.docstring = getattr(fnc, '__doc__', None) or ''
        self.defaults = {}  # default kwargs parsed command
        self.wait_for_page = True  # wait for ongoing page load before running
        self._original_name = self.name

    def __eq__(self, other):
        """
        Test equality of SeleniumCommandType instances: equal if `fnc` and `defaults` attributes are equal.
        """
        if isinstance(other, self.__class__):
            return self.fnc == other.fnc and self.defaults == other.defaults
        return False

    def __repr__(self):
        extra = '' if self.name == self._original_name else ' renamed to %r' % self.name
        return '<%s wrapping %s%s>' % (self.__class__.__name__, self.fnc, extra)


class seleniumcommand(SeleniumCommand):
    """
    Decorator can be used to encapsulate selenium command functions (or `command_class` instances) in order to expand
    parameters with values in storedVariables dictionary and wait for page changes when necessary.

    Can be used for decorating methods (descriptor usage) and other callables (callable class wrapper).

    An alternative version with `wait_for_page` attribute setted to False at `seleniumcommand.nowait`.

    This decorator returns a function with signature `(driver_instance, target=None, value=None)`, with the related
    `command_class` instance assigned to `command` function attribute.
    """
    @classmethod
    def nowait(cls, fnc):
        command = SeleniumCommand(fnc)
        command.wait_for_page = False
        return cls(command)

    def __new__(cls, fnc):
        sel_cmd = fnc if isinstance(fnc, SeleniumCommand) else SeleniumCommand(fnc)

        def wrapped(driver, target=None, value=None):
            """
            @type driver: SeleniumDriver
            """
            v_target = target  # driver._expandVariables(target) if target else target
            v_value = value   # driver._expandVariables(value) if value else value
            if sel_cmd.wait_for_page:
                driver.wait_pageload()
            logger.info('%s(%r, %r)' % (sel_cmd.name, target, value))
            return sel_cmd.fnc(driver, v_target, v_value, **sel_cmd.defaults)

        wrapped.command = sel_cmd
        wrapped.__name__ = sel_cmd.name
        wrapped.__doc__ = sel_cmd.docstring
        return wrapped


class SeleniumMultiCommandType(SeleniumCommand):
    """
    Object that encapsulates a generic selenium command (those prefixed by 'get' and 'is' in Selenium prototype),
    includes a classmethod `discover` which puts all related methods in class given as parameter and can be used
    as decorator or metaclass.

    It's intended for decorating proto-command methods that spawns multiple Selenium core commands.
    """
    prefix_docstring = {}
    suffix_docstring = {}
    contains_docstring = {}

    def _docstring(self, name, inverse=False):
        """
        Look for suffixes and prefixes in given proto-command name and completes docstring.

        @param name: proto-command name
        @param inverse: True if command modifier means negation, False otherwise (default)
        @return completed docstring
        """
        docstring = self.fnc.__doc__ or ''
        for test, docdict in (
          (name.startswith, self.prefix_docstring),
          (name.endswith, self.suffix_docstring),
          (name.__contains__, self.contains_docstring)
          ):
            for part, (regular_docstring, inverse_docstring) in six.iteritems(docdict):
                if test(part):
                    extra = inverse_docstring if inverse and inverse_docstring else regular_docstring
                    docstring = '%s\n\n%s' % (extra.rstrip('\n'), docstring.lstrip('\n'))
                    break
        return docstring

    def _wrapper(self, name, fnc=None, waitDefault=None, **kw):
        """
        Apply `seleniumcommand` attribute to given callable

        @param name: final command name
        @param fnc: wrapped proto-command
        @param waitDefault: True if command should wait for ongoing loads before executing, False otherwise (default)
        @param inverse: True if callable involves negation of original proto-command, False otherwise (default)
        @param **kw: extra keyword arguments will be forwarded to given function
        @return command_decorated function (defined by `seleniumcommand` itself)
        """
        command = SeleniumCommand(fnc or self.fnc)
        command.defaults.update(kw)
        command.wait_for_page = self.wait_for_page if waitDefault is None else waitDefault
        command.name = name
        command.docstring = self._docstring(name, kw.get('inverse', False))
        return seleniumcommand(command)

    def related_commands(self):
        """
        Yield specific selenium commands derived from current generic command.

        @yield attribute `command_descriptor` instance, seleniumcommand in default implementation.
        """
        yield self._wrapper(self.name)


class seleniumimperative(SeleniumMultiCommandType):
    """
    Imperative functions are those which execute stuff, return nothing and have an `AndWait` variant.

    Example:
        The selenium click() imperative has a 'clickAndWait()'-variant.
    """
    suffix_docstring = {
        'AndWait': ('Waits for a page change after command is executed.',)*2,
        }

    def _and_wait(self, driver, target=None, value=None):
        """
        @type driver: SeleniumDriver
        """
        driver.deprecate_page()
        self.fnc(driver, target, value=value)
        driver.wait_pageload()

    def related_commands(self):
        """
        Yield specific selenium commands derived from current imperative command (those with imperative actions and
        generating 'AndWait' alternative).

        @yield attribute `command_descriptor` instance, seleniumcommand in default implementation.
        """
        yield self._wrapper(self.name)
        yield self._wrapper('%sAndWait' % self.name, self._and_wait)


class seleniumgeneric(SeleniumMultiCommandType):
    """
    Generic functions are those that return values, and have get/is, verify, assert, waitFor, store, variants and their
    negative counterparts.

    Generic proto-command functions must return a tuple with expectedResult (for using in assert, verify and so on) and
    the actual value.
    """
    prefix_docstring = {
        'verify': ('Assert command returns the expected value.', 'Assert command does not return the expected value.'),
        'assert': ('Assert command returns true.', 'Assert command returns false.'),
        'waitFor': ('Wait until command returns true.', 'Wait until command returns false.'),
        'store': ('Saves result to storedVariables (accessible via javascript or string variables).', None),
        }

    def _get(self, driver, target, value=None, inverse=False):
        """
        @type driver: SeleniumDriver
        """
        expectedResult, result = self.fnc(driver, target, value=value)
        return result

    def _verify(self, driver, target, value=None, inverse=False):
        """
        @type driver: SeleniumDriver
        """
        verificationError = result = expectedResult = None
        try:
            expectedResult, result = self.fnc(driver, target, value=value)  # can raise NoAlertPresentException
        except NoAlertPresentException:
            if inverse and self.name.endswith('Present'):
                return True
            verificationError = "There were no alerts or confirmations"
        else:
            matches = driver.matches(expectedResult, result)
            if matches != inverse:
                return True

        if not verificationError:
            verb = 'did' if inverse else 'did not'
            verificationError = 'Actual value "%s" %s match "%s"' % (result, verb, expectedResult)

        logger.error(verificationError)
        driver.verification_errors.append(verificationError)
        return False

    def _assert(self, driver, target, value=None, inverse=False):
        """
        @type driver: SeleniumDriver
        """
        verb = 'did' if inverse else 'did not'
        expectedResult, result = self.fnc(driver, target, value=value)
        matches = driver.matches(expectedResult, result)
        assert matches != inverse, 'Actual value "%s" %s match "%s"' % (result, verb, expectedResult)

    def _waitFor(self, driver, target, value=None, inverse=False):
        """
        @type driver: SeleniumDriver
        """
        for i in driver.retries():
            try:
                expectedResult, result = self.fnc(driver, target, value=value)
                if i == 0:
                    logger.info('... waiting for%s %r' % (' not' if inverse else '', expectedResult))
                if driver.matches(expectedResult, result) != inverse:
                    return
            except NOT_PRESENT_EXCEPTIONS:
                if inverse:
                    return

    def _store(self, driver, target, value=None):
        """
        @type driver: SeleniumDriver
        """
        expectedResult, result = self.fnc(driver, target, value=value)
        # for e.g. 'storeConfirmation' the variable name will be provided in 'target' (with 'value' being None),
        # for e.g. 'storeText' the variable name will be given in 'value' (target holds the element identifier)
        # The the heuristic is to use 'value' preferably over 'target' if available. Hope this works ;-)
        variableName = value or target
        logger.info('... %s = %r' % (variableName, result))
        driver.storedVariables[variableName] = result

    def related_commands(self):
        """
        Yield specific selenium commands derived from current generic command.

        @yield attribute `command_descriptor` instance, seleniumcommand in default implementation.
        """
        inverse_names = {'Not%s' % self.name}
        for attribute in ('Present', 'Visible', 'SomethingSelected'):
            if attribute in self.name:
                inverse_names.add(self.name.replace(attribute, 'Not%s' % attribute))
                verb = 'is%s'
                break
        else:
            verb = 'get%s'

        yield self._wrapper(verb % self.name, self._get)
        yield self._wrapper('verify%s' % self.name, self._verify)
        yield self._wrapper('assert%s' % self.name, self._assert)
        yield self._wrapper('waitFor%s' % self.name, self._waitFor, waitDefault=False)
        yield self._wrapper('store%s' % self.name, self._store)

        for inverse_name in inverse_names:
            yield self._wrapper('verify%s' % inverse_name, self._verify, inverse=True)
            yield self._wrapper('assert%s' % inverse_name, self._assert, inverse=True)
            yield self._wrapper('waitFor%s' % inverse_name, self._waitFor, inverse=True, waitDefault=False)

        if self.name == 'Expression':
            yield self._wrapper('store', self._store)
