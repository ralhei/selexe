
import os
import sys
import functools
import logging
import argparse

from six.moves import UserString

from . import selexe_runner


SUCCESS = logging.ERROR + 1
logger = logging.getLogger(__name__)


class TTYColorFormat(UserString):
    fmt = '[ %(color)s%(level)s%(reset)s ] %%(message)s'
    data = fmt % {'color': '', 'level': '%s(levelname)s', 'reset': ''}
    colors = {
        'ERROR': '\x1b[31m',
        'WARNING': '\x1b[31m',
        'INFO': '\x1b[36m',
        'DEBUG': '\x1b[34m',
        'SUCCESS': '\x1b[32m',
        'NOTSET': '\x1b[37m',
        'reset': '\x1b[0m',
        }
    custom_levels = {
        SUCCESS: 'SUCCESS'
    }

    def __init__(self):
        plat = sys.platform
        supported_platform = plat != 'Pocket PC' and (plat != 'win32' or 'ANSICON' in os.environ)
        is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        self.supported = supported_platform and is_a_tty

    def __mod__(self, data):
        levelname = self.custom_levels.get(data['levelno'], data['levelname'])
        if self.supported:
            color = self.colors.get(levelname, self.colors['NOTSET'])
            reset = self.colors['reset']
        else:
            color = ''
            reset = ''
        return self.fmt % {'color': color, 'level': levelname, 'reset': reset} % data


class WebdriverAction(argparse.Action):
    drivers = sorted(selexe_runner.SelexeRunner.webdriver_classes)
    default = ['firefox']

    def __init__(self, option_strings, dest, required=False, help=None, metavar=None):
        super(WebdriverAction, self).__init__(option_strings=option_strings, dest=dest, default=self.default,
                                              choices=self.drivers, nargs=1, required=required,
                                              help=help, metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class VerbosityAction(argparse.Action):
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    default = levels[0]

    def __init__(self, option_strings, dest, required=False, help=None, metavar=None):
        super(VerbosityAction, self).__init__(option_strings=option_strings, dest=dest, default=self.default,
                                              nargs=0, required=required, help=help, metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        prev = getattr(namespace, self.dest, None)
        next = self.default if prev is None else self.levels[min(self.levels.index(prev)+1, len(self.levels)-1)]
        setattr(namespace, self.dest, next)


class SizeAction(argparse.Action):
    default = (1280, 720)

    def __init__(self, option_strings, dest, required=False, help=None, metavar=None):
        super(SizeAction, self).__init__(option_strings=option_strings, dest=dest, default=self.default,
                                         nargs=1, required=required, help=help, metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        width, height = values[0].split('x')
        value = (int(width), int(height))
        setattr(namespace, self.dest, value)


class SelexeArgumentParser(argparse.ArgumentParser):
    """Customized ArgumentParser for selexe"""
    def __init__(self):
        super(SelexeArgumentParser, self).__init__(description='Run Selenium IDE test files using webdriver')
        self.add_main_args(self.add_argument)
        self.add_cli_args(self.add_argument)

    @staticmethod
    def add_main_args(add):
        """Add command line arguments useful for both the CLI version and the one embedded in pytest-selexe

        :param add: A function (e.g. ArgumentParser.add_argument() or pytest's Parser.addoption())
        """
        add('--timeit', action='store_true', default=False,
            help='measure time each command takes to execute, implies -v')
        add('--driver', '-D', dest='drivers', action=WebdriverAction,
            help='choose selenium driver, defaults to firefox')
        add('--baseuri', '-U', action='store', default=None,
            help='base URI of server to run the selenium tests, ie. "http://localhost:8080"')
        add('--useragent', action='store', default=None,
            help='selenium browser useragent')
        add('--pmd', action='store_true', default=False,
            help='postmortem debugging')
        add('--selexe-fixtures', '-F', action='store',
            help='python module containing setUp(driver) and/or tearDown(driver) fixture functions')
        add('--size', '-S', metavar="WIDTHxHEIGHT", action=SizeAction,
            help='selenium browser window size, ie. 1280x720')

    @staticmethod
    def add_cli_args(add):
        """Add command line arguments useful only for the CLI version of selexe

        :param add: A function (e.g. ArgumentParser.add_argument() or pytest's Parser.addoption())
        """
        add('--verbose', '-v', action=VerbosityAction,
            help='verbosity level, accumulated, ie. -vvv')
        add('--print-implemented-methods', action='store_true', default=False,
            help='Print list of currently implemented selese methods in selenium driver and exit.')
        add('paths', metavar='PATH', nargs='*',
            help='Selenium IDE file paths')


def print_implemented_methods():
    """Print an alphabetically sorted list of implemented selenese methods in selenium driver"""
    from .selenium_driver import SeleniumDriver
    supported_methods = []
    for attr in SeleniumDriver.__dict__:
        method = getattr(SeleniumDriver, attr)
        try:
            # Set wait_for_page to False so that we can call 'method' further down without real driver instance
            method.command.wait_for_page = False
        except AttributeError:
            # no such command attribute, i.e. method is not a SeleniumCommand
            continue

        try:
            method(None)
        except NotImplementedError:
            # this method is only a stub and not implemented yet, so ignore it
            continue
        except:  # noqa
            # This method just fails be cause we have not called it correctly. However it is at this
            # stage very likely that this is a properly implemented selenese command.
            supported_methods.append(attr)
    supported_methods.sort()
    print('\n'.join(supported_methods))


def main(argv=None):
    """
    Selexe command-line entry point

    @param argv: list of command line arguments (excluding command), defaults to sys.argv slice
    @raise SystemExit on completion
    """
    args = SelexeArgumentParser().parse_args(sys.argv[1:] if argv is None else argv)

    if args.print_implemented_methods:
        print_implemented_methods()
        exit()

    maxlevel = (logging.INFO if args.timeit else logging.ERROR)
    level = min(maxlevel, args.verbose, args.logging)

    # Create handler with TTYColorFormat
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt=TTYColorFormat(), datefmt=None))
    handler.setLevel(level)

    # Configure selenium logger if verbosity is 2
    if level < logging.INFO:
        logger = logging.getLogger('selenium')
        logger.setLevel(level)
        logger.addHandler(handler)
        logger.propagate = False

    # Configure root logger
    logger = logging.getLogger('selexe')
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False

    # Run selenium tests
    failed = 0
    for path in args.paths:
        for driver in args.drivers:
            runner = selexe_runner.SelexeRunner(path, baseuri=args.baseuri, pmd=args.pmd, fixtures=args.fixtures,
                                                timeit=args.timeit, driver=driver, window_size=args.size,
                                                useragent=args.useragent)
            try:
                errors = runner.run()
            except KeyboardInterrupt:
                raise
            except Exception as msg:
                errors = "Running %s failed with %s\n" % (path, str(msg))
            if errors:
                failed += 1
                logging.error("Verification errors in %s %s: %s\n" % (driver, path, errors))

    # Result reporting
    log = logger.error if failed else functools.partial(logger.log, SUCCESS)
    text = ('failed' if failed else 'passed')
    if len(args.paths) == 1:
        log('Test file %s.' % text)
    elif failed:
        log('%d of %d test files failed.' % (failed, len(args.paths)))
    else:
        log('All %d test files passed.' % len(args.paths))

    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
