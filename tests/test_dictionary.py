#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
import text


class Test(unittest.TestCase):
    def runTr(self, table, words, alt):
        for i in range(len(words)):
            self.assertEqual(alt[i], list(table(words, i)))

    def test_word_translation(self):
        table = text.dictionary.WordTranslation()

        table.add(['van'], ['v'])
        table.add(['de'], ['d'])
        self.runTr(table, 'a van de b'.split(' '), [[], [(('v',), 1)], [(('d',), 1)], []])

        table.add(['van', 'de'], ['vd'])
        self.runTr(table, 'a van de b'.split(' '), [[], [(('v',), 1), (('vd',), 2)], [(('d',), 1)], []])

        table.add(['a'], ['A'])
        table.add(['b'], ['B'])
        self.runTr(table, 'a b'.split(' '), [[(('A',), 1)], [(('B',), 1)]])

    def test_postfix_translation(self):
        table = text.dictionary.PostfixTranslation()

        table.add('laan', 'ln')
        self.runTr(table, 'dennenlaan'.split(' '), [[(('dennenln',), 1)]])

        table.add('laan', 'LAAN')
        self.runTr(table, 'dennenlaan'.split(' '), [[(('dennenln',), 1), (('dennenLAAN',), 1)]])

    def test_aggregated_translation(self):
        tabword = text.dictionary.WordTranslation()
        tabword.add(['aan'], ['a'])
        tabword.add(['de'], ['d'])
        tabword.add(['aan', 'de'], ['ad'])
        tabword.add(['aan', 'de'], ['a/d'])
        tabword.add(['dennenlaan'], ['DENNENLAAN'])
        tabpost = text.dictionary.PostfixTranslation()
        tabpost.add('laan', 'ln')

        table = text.dictionary.AggregatedTranslation(tabword, tabpost)

        self.runTr(table, 'alphen aan de dennenlaan'.split(' '), [[], [(('a',), 1), (('ad',), 2), (('a/d',), 2)], [(('d',), 1)], [(('DENNENLAAN',), 1), (('dennenln',), 1)]])

    def runDict(self, haystack, lookupdict, expected):
            tokens = haystack.split(' ')
            emit = []
            states = []
            for i in range(len(tokens)):
                token = tokens[i]
                states = lookupdict._token(token, init_passthru=[], states=states)
                for state in states:
                    state.passthru.append(token)
                    if state.emit:
                        emit.append(state.emit)

            self.assertEqual(expected, emit)

    def test_dictionary(self):
        full_results = ['DENNENLAAN', 'ALPHEN']

        with text.dictionary.Dictionary(':memory:', case_sensitive=False, reset=True) as d:
            d.add(['dennenlaan'], 'DENNENLAAN')
            d.add('alphen aan den rijn'.split(' '), 'ALPHEN')
            self.runDict('', d, [])
            self.runDict('de dennenlaan in alphen aan den rijn', d, full_results)

        tabword = text.dictionary.WordTranslation()
        tabword.add(['aan'], ['a'])  # single word abbreviation
        tabword.add(['den'], ['d'])  # single word abbreviation
        tabword.add(['aan', 'den'], ['ad'])  # multi to single word abbreviation
        tabword.add(['aan', 'den'], ['a/d'])
        tabword.add(['dennenlaan'], ['dennelaan'])
        tabword.add(['dennenlaan'], ['dennen', 'laan'])  # single to multi word abbreviation
        tabpost = text.dictionary.PostfixTranslation()
        tabpost.add('laan', 'ln')

        table = text.dictionary.AggregatedTranslation(tabword, tabpost)

        with text.dictionary.Dictionary(':memory:', case_sensitive=False, reset=True) as d:
            d.add(['dennenlaan'], 'DENNENLAAN', expand=table)
            d.add('alphen aan den rijn'.split(' '), 'ALPHEN', expand=table)

            self.runDict('de dennenlaan in alphen aan den rijn', d, full_results)  # plain lookup
            self.runDict('de dennelaan in alphen aan den rijn', d, full_results)  # single word abbreviation
            self.runDict('de dennelaan in alphen a d rijn', d, full_results)
            self.runDict('de dennelaan in alphen ad rijn', d, full_results)  # multi to single word
            self.runDict('de dennelaan in alphen a/d rijn', d, full_results)
            self.runDict('de dennenln in alphen a/d rijn', d, full_results)
            self.runDict('de dennen laan in alphen aan den rijn', d, full_results)  # single to multi word
            self.runDict('dennenln', d, ['DENNENLAAN'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
