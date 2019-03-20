
import os
import sys
import functools
import logging
import argparse

from six.moves import UserString

import selexe_runner


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

    def __init__(self, option_strings, dest, required=False, help=None, metavar=None, default=None):
        super(WebdriverAction, self).__init__(option_strings=option_strings, dest=dest, default=default,
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


class DeprecatedLoggingAction(argparse.Action):
    levels = {
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'success': SUCCESS,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        }
    default = levels['error']
    deprecated_by = '--verbose'

    def __init__(self, option_strings, dest, metavar=None):
        super(DeprecatedLoggingAction, self).__init__(option_strings=option_strings, dest=dest, default=self.default,
                                                      choices=self.levels.keys(), nargs=1, required=False,
                                                      help=argparse.SUPPRESS, metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        logger.warning('%s option is deprecated, use %s instead' % (option_string, self.deprecated_by))
        value = self.levels.get(values, self.default)
        setattr(namespace, self.dest, value)


class DeprecatedAction(argparse.Action):
    def __init__(self, option_strings, dest, metavar=None):
        super(DeprecatedAction, self).__init__(option_strings=option_strings, dest=dest, default=None,
                                               choices=None, nargs=0, required=False,
                                               help=argparse.SUPPRESS, metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        logging.warning('%s option is deprecated, is no longer necessary' % option_string)


class SelexeArgumentParser(argparse.ArgumentParser):
    webdriver_action_class = WebdriverAction
    verbosity_action_class = VerbosityAction
    logging_action_class = DeprecatedLoggingAction
    selexe_action_class = DeprecatedAction
    def __init__(self):
        super(SelexeArgumentParser, self).__init__(description='Run Selenium IDE test files using webdriver')
        add = self.add_argument
        add('--timeit', action='store_true', default=False,
            help='measure time each command takes to execute, implies -v')
        add('--driver', '-D', dest='drivers', action=self.webdriver_action_class, default=['firefox'],
            help='choose selenium driver, defaults to firefox')
        add('--baseuri', '-U', action='store', default=None,
            help='base URI of server to run the selenium tests, ie. "http://localhost:8080"')
        add('--pmd', action='store_true', default=False,
            help='postmortem debugging')
        add('--verbose', '-v', action=self.verbosity_action_class,
            help='verbosity level, accumulated, ie. -vvv')
        add('--fixtures', '-F', action='store',
            help='python module containing setUp(driver) and/or tearDown(driver) fixture functions')
        add('paths', metavar='PATH', nargs='+',
            help='Selenium IDE file paths')
        # deprecated
        add('--logging', action=self.logging_action_class)
        add('--selexe', action=self.selexe_action_class)


def main(argv=None):
    """
    Selexe command-line entry point

    @param argv: list of command line arguments (excluding command), defaults to sys.argv slice
    @raise SystemExit on completion
    """
    args = SelexeArgumentParser().parse_args(sys.argv[1:] if argv is None else argv)
    maxlevel = (logging.INFO if args.timeit else logging.ERROR)
    level = min(maxlevel, args.verbose, args.logging)

    # Create handler with TTYColorFormat
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt=TTYColorFormat(), datefmt=None))
    handler.setLevel(level)

    # Configure selenium logger if verbosity is 2
    if level < logging.info:
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
                                                timeit=args.timeit, driver=driver)
            errors = runner.run()
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
