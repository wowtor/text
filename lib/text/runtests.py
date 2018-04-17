#!/usr/bin/env python3

import argparse
import logging
import os
import unittest

from . import dictionary
from . import nladressen


def sqlFirst(con, q):
    cur = con.cursor()
    try:
        cur.execute(q)
        return cur.fetchall()[0][0]
    finally:
        cur.close()


class TestDictionary(unittest.TestCase):
    def test_dict(self):
        with dictionary.Dictionary('__test.db', case_sensitive=True, reset=True) as dict:
            dict.add(['a'], 'a!')
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM word'), 1)
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM emit'), 1)

            dict.add(['b'], 'b!')
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM word'), 2)
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM emit'), 2)

            dict.add(['b'], 'b!!')
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM word'), 2)
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM emit'), 3)

            dict.add(['a', 'x'], 'ax!')
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM word'), 3)
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM emit'), 4)

            dict.add(['a', 'y'], 'ay!')
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM word'), 4)
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM emit'), 5)

            dict.add(['x', 'y'], 'xy!')
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM word'), 6)
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM emit'), 6)

            dict.add(['a', 'b'], 'ab!')
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM word'), 7)
            self.assertEqual(sqlFirst(dict._con, 'SELECT COUNT(*) FROM emit'), 7)

            states = []
            states = dict.token('a', 0, states)
            self.assertEqual('a!', '/'.join([state.emit for state in states if state.emit]))

            states = dict.token('x', 0, states)
            self.assertEqual('ax!', '/'.join([state.emit for state in states if state.emit]))

            states = dict.token('z', 0, states)
            self.assertEqual('', '/'.join([state.emit for state in states if state.emit]))

    def tearDown(self):
        if os.path.exists('__test.db'):
            os.remove('__test.db')


class TestStraatnaam(unittest.TestCase):
    def test_expansinon(self):
        triples = [
            ('van der meerstraat'.split(' '), 0, [('v',1)]),
            ('van der meerstraat'.split(' '), 1, [('d',1)]),
            ('van der meerstraat'.split(' '), 2, [('meerstr',1)]),
        ]
        nladressen.loadExpansionTable()
        for words, offset, expected in triples:
            expected.sort()
            actual = sorted(list(nladressen.expandStraatnaamWord(words, offset)))
            self.assertEqual(expected, actual)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser('gate')
    parser.add_argument('-v', action='count', default=0)
    parser.add_argument('-q', action='count', default=0)
    args = parser.parse_args()

    verbosity = args.v - args.q
    if verbosity > 0:
        logging.getLogger().setLevel(logging.DEBUG)

    unittest.main()
