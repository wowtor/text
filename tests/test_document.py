#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
import text


class Test(unittest.TestCase):
    def test_builder(self):
        builder = text.document.DocumentBuilder()
        builder.addToken('a')
        self.assertEqual(1, len(builder.toDocument().annotations))
        self.assertEqual(1, len([a for a in builder.toDocument().annotations]))

        builder.addToken(' ')
        builder.addToken('b')
        builder.addToken('.')
        self.assertEqual(['a', ' ', 'b', '.'], [a.features['string'] for a in builder.toDocument().annotations])
        self.assertEqual(['a', 'b'], [a.features['string'] for a in builder.toDocument().annotations.by_type['token']])
        self.assertEqual(['token', 'space', 'token', 'punct'], [a.type for a in builder.toDocument().annotations])

        tokens = builder.toDocument().annotations.selectType('token')
        self.assertEqual(['a', 'b'], [a.features['string'] for a in tokens])
        self.assertEqual([0, 2], tokens._all_keys)
        self.assertEqual([0, 2], tokens.by_type_keys['token'])

        tokens = builder.toDocument().annotations.selectOffset(2, 3)
        self.assertEqual(['b'], [a.features['string'] for a in tokens])
        self.assertEqual([2], tokens._all_keys)
        self.assertEqual([2], tokens.by_type_keys['token'])

        builder.addToken('xxx')
        builder.addToken('yyy')
        builder.addToken('.')
        self.assertEqual([0, 1, 2, 3, 4, 7, 10], builder.toDocument().annotations._all_keys)
        tokens = builder.toDocument().annotations.selectOffset(3, 6)
        self.assertEqual(['.', 'xxx'], [a.features['string'] for a in tokens])

        tokens = builder.toDocument().annotations.selectOffset(4, 6)
        self.assertEqual(['xxx'], [a.features['string'] for a in tokens])

        tokens = builder.toDocument().annotations.selectOffset(5, 6)
        self.assertEqual(['xxx'], [a.features['string'] for a in tokens])

        tokens = builder.toDocument().annotations.selectOffset(5, 7)
        self.assertEqual(['xxx'], [a.features['string'] for a in tokens])

        tokens = builder.toDocument().annotations.selectOffset(5, 8)
        self.assertEqual(['xxx', 'yyy'], [a.features['string'] for a in tokens])


    def test_document(self):
        doc = text.document.Document('Dit is een klein tekstje, met een komma.')
        text.tokenizer.Tokenizer().process(doc)
        self.assertEqual(len(doc.annotations), 17)
        self.assertEqual(len([a for a in doc.annotations]), 17)
        self.assertEqual([0, 3, 4, 6, 7, 10, 11, 16, 17, 24, 25, 26, 29, 30, 33, 34, 39], doc.annotations._all_keys)

        doc.annotations.add(text.document.Annotation('test', (7, 24), {}))
        self.assertEqual([7, 7, 10, 11, 16, 17], doc.annotations.selectOffset(7, 24)._all_keys)


if __name__ == '__main__':
    unittest.main(verbosity=2)