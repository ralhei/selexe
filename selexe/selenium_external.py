"""
External WebElement utils
-------------------------
This module provides utility classes and functions for dealing with selenium WebElement located on windows different
than current one.

Selenium usually fails when a driver action, or some element actions, are performed when driver is on a different
window. This behavior isn't a problem unless we are dealing with frames.

As Selenium IDE works with frame content as it would be part of the current document, we need to provide window
auto-switching functionality, in addition to store where an element belongs to.
"""
import logging
import functools
import six

from selenium.webdriver.remote.webelement import WebElement


logger = logging.getLogger(__name__)


class DummyContext(object):
    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        if type:
            raise value


class ExternalContext(object):
    """
    Context manager will make driver to switch to frame or window on enter, and restore original window on leave.
    """
    __slots__ = ('driver', 'frame_element', 'window_handle', '_default_handle')

    _stack = []

    dummy_context_class = DummyContext

    def __new__(cls, driver, frame_element=None, window_handle=None):
        if cls._stack and cls._stack[-1].driver == driver and cls._stack[-1].frame_element == frame_element and cls._stack[-1].window_handle == window_handle:
            # Optimization: avoid context if already on similar context
            return DummyContext()
        return super(ExternalContext, cls).__new__(cls)

    def __init__(self, driver, frame_element=None, window_handle=None):
        """
        @param driver: selenium driver
        @param frame_element: selenium WebElement pointing to frame element
        @param window_handle: window handle id as string
        """
        self.driver = driver
        self.frame_element = frame_element
        self.window_handle = window_handle
        self._default_handle = None

    def __enter__(self):
        self._stack.append(self)
        self._default_handle = self.driver.current_window_handle
        if self.frame_element:
            self.driver.switch_to.frame(self.frame_element)
        elif self.window_handle:
            self.driver.switch_to.window(self.window_handle)

    def __exit__(self, type, value, traceback):
        self.driver.switch_to.window(self._default_handle)
        if self.frame_element:
            self.driver.switch_to.default_content()
        self._stack.remove(self)
        if type:
            raise value


class ExternalElement(WebElement):
    """
    Base wrapper which simplify using elements not belonging to current window, switching to container window
    automatically when needed.
    """
    __slots__ = ('_parent', '_id', '_frame_element', '_window_handle')

    context_class = ExternalContext

    @classmethod
    def from_webelement(cls, webelement, frame_element=None, window_handle=None):
        """
        Generate ExternalElement from an WebElement object

        @param webelement: selenium.remote.webelement.WebElement object
        @param frame_element: element whose object belongs to.
        @param window_handle:element whose object belongs to.
        @return: instance
        """
        return cls(webelement._parent, webelement._id, frame_element, window_handle)

    def __init__(self, parent, id_, frame_element=None, window_handle=None):
        """
        Generate object which stores a wrapped object and owner frame_element or window_handle.
   
        @param parent: selenium.webdriver.Remote driver object.
        @param id_: selenium object internal id
        @param frame_element: element whose object belongs to.
        @param window_handle: element whose object belongs to.
        """
        super(ExternalElement, self).__init__(parent, id_)
        self._frame_element = frame_element
        self._window_handle = window_handle

    @property
    def _context(self):
        """
        Get context for current External object
        @return: context manager
        """
        return self.context_class(self._parent, self._frame_element, self._window_handle)

    def _wrap(self, o):
        """
        Decorator which wraps given object into ExternalContext manager

        @param o: object to wrap
        @return: wrapped function
        """
        if isinstance(o, ExternalElement):
            return o
        elif isinstance(o, WebElement):
            return self.__class__.from_webelement(o, self._frame_element, self._window_handle)
        elif callable(o):
            @functools.wraps(o)
            def wrapped(*args, **kwargs):
                with self._context:
                    return self._wrap(o(*args, **kwargs))
            return wrapped
        elif not isinstance(o, (six.string_types, dict)) and hasattr(o, '__iter__'):
            return map(self._wrap, o)
        return o

    def __getattribute__(self, item):
        if item  == '__class__' or item in self.__class__.__dict__:
            # filter non-inherited attributes
            return super(ExternalElement, self).__getattribute__(item)
        # wrap inherited attributes
        r = getattr(super(ExternalElement, self), item)
        return self._wrap(r)


def element_context(element):
    """
    Utility function

    @param element:
    @return:
    """
    if hasattr(element, '_context'):
        return element._context
    return DummyContext()

def original_element(element):
    """
    Utility function

    @param element:
    @return:
    """
    if hasattr(element, '_wrapped'):
        return element._wrapped
    return element