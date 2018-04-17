#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import os

import bottle

TEXT_DOCUMENT = None


STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')


@bottle.route('/')
def root():
    return bottle.static_file('index.html', root=STATIC_ROOT)


@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root=STATIC_ROOT)


@bottle.route('/api')
def api():
    bottle.response.content_type = 'application/json'
    with open(TEXT_DOCUMENT, 'rb') as f:
        return f.read()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='count', default=0)
    parser.add_argument('-q', action='count', default=0)
    parser.add_argument('document', nargs=1, help='document to view in the browser')
    args = parser.parse_args()

    verbosity = args.v - args.q
    loglevel = logging.WARNING+(args.q-args.v)*10
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(processName)s: %(module)s: %(message)s', level=loglevel)

    TEXT_DOCUMENT = args.document[0]
    bottle.run(host='localhost', port=8080)
