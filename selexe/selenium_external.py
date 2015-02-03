
import logging
import functools


logger = logging.getLogger(__name__)


class ExternalContext(object):
    """
    Context manager will make driver to switch to iframe or window on enter, and restore original window on leave.
    """
    def __init__(self, driver, iframe_element=None, window_handle=None):
        self.driver = driver
        self.iframe_element = iframe_element
        self.window_handle = window_handle

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

    def _decorate(self, fnc):
        """
        Decorator which wraps given function into ExternalContext manager

        :param fnc: fnc to wrap
        :return: wrapped function
        """
        @functools.wraps(fnc)
        def wrapped(*args, **kwargs):
            with self.context_class(self._driver, self._iframe_element, self._window_handle):
                return fnc(*args, **kwargs)
        return wrapped


class ExternalElement(ExternalObject):
    """
    Element wrapper which run __getattr__ commands inside ExternalContext manager, and decorates returned callable
    objects.
    """
    def __getattr__(self, item):
        with self._context:
            r = getattr(self._wrapped, item)
        if callable(r):
            return self._decorate(r)
        return r