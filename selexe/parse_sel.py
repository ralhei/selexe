import BeautifulSoup


class SeleniumParser(object):
    def __init__(self, fp):
        self.fp = fp
        self.soup = BeautifulSoup.BeautifulSoup(fp.read())
        baseUrlLink = self.soup.find('link', attrs={'rel': 'selenium.base'})
        self.baseuri = baseUrlLink['href'] if baseUrlLink else None

    def __iter__(self):
        body = self.soup.find('tbody')
        for tr in body.findAll('tr'):
            # return tuple (command, target, value) -> this corresponds to column names in Selenium IDE
            t = tuple([(td.string) for td in tr.findAll('td')])
            #t = tuple([td.text for td in tr.findAll('td')])
            yield t



if __name__ == '__main__':
    import sys
    fp = open(sys.argv[1])
    p = SeleniumParser(fp)
    print list(p)
