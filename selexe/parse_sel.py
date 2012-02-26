import BeautifulSoup


class SeleniumParser(object):
    def __init__(self, fp):
        self.fp = fp
        self.soup = BeautifulSoup.BeautifulSoup(fp.read())
        self.baseuri = self.soup.find('link', attrs={'rel': 'selenium.base'})['href']

    def __iter__(self):
        body = self.soup.find('tbody')
        for tr in body.findAll('tr'):
            # return tuple (command, target, value) -> this corresponds to column names in Selenium IDE
            t = tuple([(td.string) for td in tr.findAll('td')])
            yield t



if __name__ == '__main__':
    fp = open('testfiles/vector.sel')
    p = SeleniumParser(fp)
    print list(p)
