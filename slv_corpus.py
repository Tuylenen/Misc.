from ..params_container import Container
from ..target import Target

from requests import get
from bs4 import BeautifulSoup
from html import unescape
import re


__author__ = 'Oxana Kovaleva'
__doc__ = \
"""
    
API for Slovene corpus (http://nl.ijs.si/noske/all.cgi/first_form).
    
Args:
    query: str or List([str]): query or queries (currently only exact search by word or phrase is available)
    numResults: int: number of results wanted (100 by default)
    kwic: boolean: kwic format (True) or a sentence (False) (True by default)
    tag: boolean: whether to collect grammatical tags for target word or not (False by default, available only for corbama-net-non-tonal subcorpus)
    
Main function: extract
Returns:
    A generator of Target objects.

"""


TEST_QUERIES = {'test_single_query': 'rosno',
                'test_multi_query': ['rosno', 'mlad']
               }


class PageParser(Container):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.subcorpus is None:
            self.subcorpus = 'kres'
        if self.kwic:
            self.__viewmode = 'kwic'
        else:
            self.__viewmode = 'sen'
            
        self.__page = None
        self.__pagenum = 1

        
    def __get_results(self):
        params = {
            "corpname": self.subcorpus,
            "iquery": self.query,
            "fromp": self.__pagenum,
            "viewmode": self.__viewmode
        }
        """
        create a query url and get results for one page
        """
        r = get('http://nl.ijs.si/noske/all.cgi/first', params)
        return unescape(r.text)


    def __parse_page(self):
        """
        find results (and total number of results) in the page code
        """
        soup = BeautifulSoup(self.__page, 'lxml')
        if soup.select('div#error'):
            return []
        res = soup.find_all('table')[2]
        res = res.find_all('tr')
        if self.__pagenum == 1:
            self.numResults = min(int(soup.find_all('strong')[-1].text.replace(u'\xa0', u'').replace(u',', u'')),
                                  self.numResults)
        return res
 
    def __parse_result(self, result):
        """
        find hit and extract the sentence it is in
        """
        sentenceEnders = re.compile('[.!?]')
        lc = ' '.join([x.text.strip() for x in result.select('td.lc span.nott')])
        lc = re.split(sentenceEnders, lc)[-1].strip()
        kws = result.b.text.strip(' ')
        tags_str = result.findAll('b')[1].text.strip().split('/')
        tags = {'lemma': tags_str[1], 'PoS': tags_str[2][0], 'tag': tags_str[2][1:]}
        rc = ' '.join([x.text.strip() for x in result.select('td.rc span.nott')])
        rc = re.split(sentenceEnders, rc)[0].strip()
        idxs = (len(lc) + 1, len(lc) + 1 + len(kws))
        text = ' '.join([lc, kws, rc])
        t = Target(text, idxs, result.td.text, tags)
        return t
    
    
    def extract(self):
        n = 0
        while n < self.numResults:
            self.__page = self.__get_results()
            rows = self.__parse_page()
            if not rows:
                break
            r = 0
            while n < self.numResults and r < len(rows):
                yield self.__parse_result(rows[r])
                n += 1
                r += 1
            self.__pagenum += 1
