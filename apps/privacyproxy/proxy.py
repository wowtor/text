#!/usr/bin/env python

# http://stackoverflow.com/questions/9465236/python-twisted-proxy-and-modifying-content

import logging
import re

from twisted.python import log
from twisted.web import http, proxy
import bs4

import text


def filter(s):
    return s.upper()


def filterContents(elem):
    for contents in elem.find_all(string=True):
        #print '-----', elem, type(elem)
        contents.replace_with(filter(contents))
    #for i in range(len(elem.contents)):
    #    contents = elem.contents[i]
    #    if contents is not None:
    #        print 'CC--', elem, '==', i, contents, type(contents)
    #        contents.replace_with(filter(contents))


class ProxyClient(proxy.ProxyClient):
    """Mangle returned header, content here.

    Use `self.father` methods to modify request directly.
    """

    def processContent(self, html):
        soup = bs4.BeautifulSoup(html, 'html.parser')
        for elem in soup.find_all('span', class_=re.compile('^(title|excerpt|caption)$')):
            filterContents(elem)
        for elem in soup.find_all('h1'):
            filterContents(elem)
        for elem in soup.find_all('div', class_=re.compile('^(molecule-headline-excerpt|item-caption|rsCaption)$')):
            filterContents(elem)
        for elem in soup.find_all('img', alt=True):
            #if elem['alt'] is not None:
             #   print '=-', elem['alt']
            elem['alt'] = filter(elem['alt'])
        return str(soup)

    def connectionMade(self):
        del self.headers['accept-encoding']
        proxy.ProxyClient.connectionMade(self)

    def handleResponsePart(self, buffer):
        print self.rest
        if self.rest.endswith('.html'):
            buffer = self.processContent(buffer)

        proxy.ProxyClient.handleResponsePart(self, buffer)


class ProxyClientFactory(proxy.ProxyClientFactory):
    protocol = ProxyClient


class ProxyRequest(proxy.ProxyRequest):
    protocols = dict(http=ProxyClientFactory)


class Proxy(proxy.Proxy):
    requestFactory = ProxyRequest

#    def headerReceived(self, line):
#        if line.startswith('Accept-Encoding:'):
#            pass
#        else:
#            proxy.Proxy.headerReceived(self, line)


class ProxyFactory(http.HTTPFactory):
    protocol = Proxy


portstr = "tcp:8080:interface=localhost"  # serve on localhost:8080

if __name__ == '__main__':
    import sys
    from twisted.internet import endpoints, reactor

    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT)

    log.startLogging(sys.stdout)
    endpoint = endpoints.serverFromString(reactor, portstr)
    d = endpoint.listen(ProxyFactory())
    reactor.run()
