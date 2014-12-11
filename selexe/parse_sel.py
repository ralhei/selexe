import re
import os
import BeautifulSoup
from htmlentitydefs import name2codepoint


class SeleniumTestCaseParser(object):
    __slots__ = ('path', 'soup', 'baseuri')
    def __init__(self, path, data):
        self.path = path
        self.soup = BeautifulSoup.BeautifulSoup(data)
        baseuri = self.soup.find('link', attrs={'rel': 'selenium.base'})
        self.baseuri = baseuri['href'].rstrip('/') if baseuri else None

    @classmethod
    def from_file(cls, fp, length=None):
        path = getattr(fp, 'name', None)
        data = fp.read() if length is None else fp.read(length)
        return cls(path, data)

    @classmethod
    def from_path(cls, path):
        with open(path, 'r') as fp:
            return cls.from_file(fp)

    def __iter__(self):
        body = self.soup.find('tbody')
        for tr in body.findAll('tr'):
            try:
                command, target, value = [td.renderContents() for td in tr.findAll('td')]
            except:
                continue
            v_value = handleTags(value)
            v_target = handleTags(target)
            v_value = htmlentitydecode(v_value)
            v_target = htmlentitydecode(v_target)
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

    def __new__(cls, fp):
        path = getattr(fp, 'name', None)
        data = fp.read()
        if 'id="suiteTable"' in data:
            return cls.testsuite_class(path, data)
        return cls.testcase_class(path, data)

    def __init__(self, *args, **kwargs):
        raise NotImplementedError('Class %s cannot be instantiated.' % self.__class__.__name__)


def htmlentitydecode(s):
    """translate all HTML entities like &nbsp; into clean text characters"""
    return re.sub('&(%s);' % '|'.join(name2codepoint), lambda m: unichr(name2codepoint[m.group(1)]), s)

def handleTags(s):
    s = re.sub("\s*<br />\s*", "\n", s)
    return re.sub("<.*>", "", s)


if __name__ == '__main__':
    import sys
    fp = open(sys.argv[1])
    p = SeleniumParser(fp)
    print list(p)
