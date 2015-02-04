
import logging
import functools
import six

from selenium.webdriver.remote.webelement import WebElement


logger = logging.getLogger(__name__)


class ExternalContext(object):
    """
    Context manager will make driver to switch to iframe or window on enter, and restore original window on leave.
    """
    __slots__ = ('driver', 'iframe_element', 'window_handle', '_default_handle')

    def __init__(self, driver, iframe_element=None, window_handle=None):
        self.driver = driver
        self.iframe_element = iframe_element
        self.window_handle = window_handle
        self._default_handle = None

    def __enter__(self):
        self._default_handle = self.driver.current_window_handle
        if self.iframe_element:
            self.driver.switch_to.frame(self.iframe_element)
        elif self.window_handle:
            self.driver.switch_to.window(self.window_handle)

    def __exit__(self, type, value, traceback):
        self.driver.switch_to.window(self._default_handle)
        if type:
            raise


class ExternalObject(object):
    """
    Base wrapper which simplify using elements not belonging to current window, switching to container window
    automatically when needed.
    """
    __slots__ = ('_wrapped', '_iframe_element', '_window_handle')

    context_class = ExternalContext

    def __init__(self, wrapped, iframe_element=None, window_handle=None):
        """
        Generate object which stores a wrapped object and owner iframe_element or window_handle.

        @param wrapped: wrapped object, can be Selenium element or selenium element method.
        @param iframe_element: element whose given wrapped object belongs to.
        @param window_handle: window id whose given wrapped object belongs to.
        """
        self._wrapped = wrapped
        self._iframe_element = iframe_element
        self._window_handle = window_handle

    @property
    def _driver(self):
        """
        Get selenium driver this external belongs to.
        """
        return getattr(self._wrapped, 'im_self', self._wrapped).parent

    @property
    def _context(self):
        """
        Get context for current External object
        :return:
        """
        return self.context_class(self._driver, self._iframe_element, self._window_handle)


class ExternalElement(ExternalObject):
    """
    Element wrapper which run __getattr__ commands inside ExternalContext manager, and decorates returned callable
    objects.
    """

    def _wrap(self, o):
        """
        Decorator which wraps given function into ExternalContext manager

        :param fnc: fnc to wrap
        :return: wrapped function
        """
        if isinstance(o, ExternalObject):
            return o
        elif callable(o):
            @functools.wraps(o)
            def wrapped(*args, **kwargs):
                with self.context_class(self._driver, self._iframe_element, self._window_handle):
                    return self._wrap(o(*args, **kwargs))
            return wrapped
        elif isinstance(o, WebElement):
            return self.__class__(o, self._iframe_element, self._window_handle)
        elif not isinstance(o, (six.string_types, dict)) and hasattr(o, '__iter__'):
            return map(self._wrap, o)
        return o

    def __getattr__(self, item):
        with self._context:
            return self._wrap(getattr(self._wrapped, item))