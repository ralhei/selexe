
import string

from ..selexe_runner import SelexeRunner

ALPHADIGIT = string.ascii_letters + string.digits

def include_selexe_tests(suite_paths):
    '''
    Include tests for all given paths into decorated class, suitable for using in conjunction with unittest frameworks.

    Appended methods rely on class 'options' dictionary, which will be passed to SelexeRunner as keyword arguments.

    Example:
    >>> import unittest
    >>> tests = (
    ...     ('file1', 'suites/something.testsuite'),
    ...     ('file2', 'suites/other.testcase'),
    ...     )
    >>>
    >>> @include_selexe_tests(tests)
    ... class MyTestCase(unittest.TestCase):
    ...     options = {'driver': 'phantomjs'}
    >>>
    >>> if __name__ == '__main__':
    ...     unittest.testmod()

    :param suite_paths: iterable of 2-d tuples with name and selenese file path.
    :return: wrapper function
    '''
    def wrapped(cls):
        '''
        Inner wrapper for 'include_selexe_tests' decorator. This function must be called with the class-to-decorate as
        its only argument.
        This function uses arguments given to 'include_selexe_tests' for adding 'test_'-prefixed methods to
        class.

        :param cls: class to decorate
        :return: given class
        '''
        for name, path in suite_paths:
            def test_suite(self):
                return SelexeRunner(path, **self.options).run()
            test_suite.__name__ = 'test_%s' % ''.join(i if i in ALPHADIGIT else '_' for i in name)
            test_suite.__doc__ = 'Selenium testsuite for %s' % name
            setattr(cls, test_suite.__name__, test_suite)
        return cls
    return wrapped