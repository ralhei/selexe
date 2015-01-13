
import re
import os
import logging
import io
import six
import bs4 as beautifulsoup
import htmlentitydefs

logger = logging.getLogger(__name__)


class SeleniumTestCaseParser(object):
    __slots__ = ('path', 'soup', 'baseuri')
    htmlentity_map = htmlentitydefs.name2codepoint
    htmlentity_compiled_re = re.compile('&(%s);' % '|'.join(htmlentity_map))
    br_compiled_re = re.compile(r"\s*<br />\s*")
    tag_compiled_re = re.compile("<.*>")

    def __init__(self, path, data):
        self.path = path
        assert isinstance(data, six.text_type), '%r is required' % six.text_type
        self.soup = beautifulsoup.BeautifulSoup(data)
        baseuri = self.soup.find('link', attrs={'rel': 'selenium.base'})
        self.baseuri = baseuri['href'].rstrip('/') if baseuri else None

    @classmethod
    def from_file(cls, fp, length=None, encoding='utf-8'):
        path, data = cls._read_fp(fp, length, encoding)
        return cls(path, data)

    @classmethod
    def from_path(cls, path, encoding='utf-8'):
        with io.open(path, 'r', encoding=encoding) as fp:
            return cls.from_file(fp)

    @classmethod
    def force_unicode(cls, data, encoding='utf-8'):
        return six.text_type(data, encoding=encoding) if isinstance(data, six.binary_type) else data

    @classmethod
    def _read_fp(cls, fp, length, encoding):
        name = getattr(fp, 'name', None)
        encoding = getattr(fp, 'encoding', encoding)
        return name, cls.force_unicode(fp.read() if length is None else fp.read(length), encoding)

    @classmethod
    def _htmlentity_translate_handler(cls, match):
        return unichr(cls.htmlentity_map[match.group(1)])

    @classmethod
    def htmlentity_translate(cls, s):
        """translate all HTML entities like &nbsp; into clean text characters"""
        return cls.htmlentity_compiled_re.sub(cls._htmlentity_translate_handler, s)

    @classmethod
    def handle_tags(cls, s):
        s = cls.br_compiled_re.sub("\n", s)
        return cls.tag_compiled_re.sub("", s)

    @classmethod
    def clean_text(cls, s):
        s = cls.handle_tags(s)
        return cls.htmlentity_translate(s)

    def __iter__(self):
        body = self.soup.find('tbody')
        for tr in body.findAll('tr'):
            try:
                command, target, value = [
                    self.force_unicode(td.renderContents(), beautifulsoup.DEFAULT_OUTPUT_ENCODING)
                    for td in tr.findAll('td')
                    ]
            except ValueError:
                logger.debug('Row %r failed' % tr, exc_info=True)
                continue
            v_value = self.clean_text(value)
            v_target = self.clean_text(target)
            yield (self.baseuri, command, v_target, v_value)


class SeleniumTestSuiteParser(SeleniumTestCaseParser):
    testcase_class = SeleniumTestCaseParser
    def iter_search_directories(self):
        yield os.getcwd()
        if self.path:
            yield os.path.dirname(os.path.abspath(self.path))

    def find_filename(self, path):
        if os.path.isabs(path):
            return path
        for base in self.iter_search_directories():
            candidate = os.path.join(base, path)
            if os.path.exists(candidate):
                return candidate
        raise IOError('File not found')

    def __iter__(self):
        body = self.soup.find('tbody')
        for tr in body.findAll('tr'):
            a = tr.find('a')
            if a:
                path = self.find_filename(a['href'])
                for baseuri, command, v_target, v_value in self.testcase_class.from_path(path):
                    yield (baseuri, command, v_target, v_value)


class SeleniumParser(SeleniumTestCaseParser):
    testcase_class = SeleniumTestCaseParser
    testsuite_class = SeleniumTestSuiteParser

    def __new__(cls, fp, length=None, encoding='utf-8'):
        return cls.from_file(fp, length, encoding) # compatibility

    def __init__(self, *args, **kwargs):
        raise NotImplementedError('Class %s cannot be instantiated.' % self.__class__.__name__)

    @classmethod
    def from_file(cls, fp, length=None, encoding='utf-8'):
        path, data = cls._read_fp(fp, length, encoding)
        if 'id="suiteTable"' in data:
            return cls.testsuite_class(path, data)
        return cls.testcase_class(path, data)

htmlentitydecode = SeleniumTestCaseParser.htmlentity_translate # compatibility
handleTags = SeleniumTestCaseParser.handle_tags # compatibility