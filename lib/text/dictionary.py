from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import json
import logging
import os
import contextlib

import sqlite3

from . import document


LOG = logging.getLogger(__file__)
#LOG.setLevel(logging.INFO)

DictionaryState = collections.namedtuple('DictionaryState', ['rowid', 'passthru', 'emit'])


class AggregatedTranslation():
    def __init__(self, *backends):
        self._backends = backends

    def __call__(self, words, offset):
        """
        Generates alternative representations of a token string of arbitrary
        length, starting at the position indicated by `offset`

        :param:words: a list of tokens representing the input string
        :param:offset: the offset of the first token considered in `words`

        :return: an iterator of tuples (alt, length), with `alt` is a tuple
        representing an alternative to the substring of `words` starting at
        `offset` with length `length`.
        """
        for b in self._backends:
            for alt, l in b(words, offset):  # yield from
                yield alt, l


class WordTranslation():
    def __init__(self):
        self._tables = []

    def add(self, canonical_words, alternative_words):
        canonical_words = canonical_words if isinstance(canonical_words, tuple) else tuple(canonical_words)
        alternative_words = alternative_words if isinstance(alternative_words, tuple) else tuple(alternative_words)

        while len(self._tables) <= len(canonical_words):
            self._tables.append(collections.defaultdict(list))

        self._tables[len(canonical_words)][canonical_words].append(alternative_words)

    def __call__(self, words, offset):
        for i in range(min(len(self._tables), len(words)-offset+1)):
            substr = tuple(words[offset:offset+i])
            if substr in self._tables[i]:
                for alt in self._tables[i][substr]:
                    yield alt, i


class PostfixTranslation():
    def __init__(self):
        self._table = collections.defaultdict(list)
        self._sizes = set()

    def add(self, postfix, abbrv):
        self._table[postfix].append(abbrv)
        self._sizes.add(len(postfix))

    def __call__(self, words, offset):
        for l in self._sizes:
            postfix = words[offset][-l:]
            if postfix in self._table:
                for alt in self._table[postfix]:
                    yield (words[offset][0:-l] + alt,), 1


class Dictionary(object):
    def __init__(self, dbfile, case_sensitive=False, reset=False):
        self.dbfile = dbfile
        self._case_sensitive = case_sensitive
        self._con = None
        self.__tainted = False

        if reset:
            self._clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_t, exc_v, trace):
        self.close()

    def _token(self, token, init_passthru, states):
        """
        :param:token: the next token string
        :param:init_passthru: a user-defined value which is assigned to every entry state
        :param:states: a list of states, with each state is a tuple (rowid, passthru)
        """
        if self._con is None:
            self._con = sqlite3.connect(self.dbfile)

        if self.__tainted:
            self._commit()

        qwheres = ['(previous_id is NULL AND word = ?)']
        qargs = [token]

        statemap = dict((state.rowid, state) for state in states)
        for stateid in statemap:
            qwheres.append('(previous_id = ? AND word = ?)')
            qargs.append(stateid)
            qargs.append(token)

        q = 'SELECT previous_id, normalized_id, emit FROM word LEFT JOIN emit ON emit.word_id = word.normalized_id WHERE %s' % ' OR '.join(qwheres)
        LOG.debug('query: %s (args: %s)' % (q, qargs))
        with contextlib.closing(self._con.cursor()) as cur:
            cur.execute(q, qargs)
            rows = cur.fetchall()
            newstates = []
            for previous, rowid, emit in rows:
                passthru = statemap[previous].passthru if previous in statemap else init_passthru
                newstates.append(DictionaryState(rowid, passthru, emit))
            return newstates

    def _commit(self):
        """
        Synchronize the underlying database.
        """
        if self._con is not None and self.__tainted:
            self._con.execute('UPDATE word SET normalized_id = rowid WHERE normalized_id is NULL')
            self._con.commit()
            self.__tainted = False

    def close(self):
        """
        Close this dictionary and any underlying database connections.
        """
        if self._con is not None:
            self._commit()
            self._con.close()
            self._con = None

    def _clear(self):
        if self._con is not None:
            self.close()

        if os.path.exists(self.dbfile):
            os.remove(self.dbfile)
            self.__tainted = False

    def _setup(self):
        if self._con is not None:
            raise ValueError('already open')

        create_tables = not os.path.exists(self.dbfile)
        self._con = sqlite3.connect(self.dbfile)

        if create_tables:
            for q in [
                '''CREATE TABLE IF NOT EXISTS word(
                    previous_id INT NULL,
                    word TEXT NOT NULL COLLATE %s,
                    normalized_id INT NULL
                )''' % ('BINARY' if self._case_sensitive else 'NOCASE'),
                'CREATE UNIQUE INDEX IF NOT EXISTS word_word ON word(previous_id, word, normalized_id)',
                '''CREATE TABLE IF NOT EXISTS emit(
                    word_id INT NOT NULL,
                    emit TEXT NOT NULL
                )''',
                'CREATE INDEX IF NOT EXISTS emit_wordid ON emit(word_id)',
            ]:
                LOG.debug('query: %s' % q)
                self._con.execute(q)

            self.__tainted = True

    def _insertWord(self, previous, word, normalized):
        with contextlib.closing(self._con.cursor()) as cur:
            qwheres = ['word = ?']
            qargs = [word]
            if previous is None:
                qwheres.append('previous_id is NULL')
            else:
                qwheres.append('previous_id = ?')
                qargs.append(previous)
            if normalized is None:
                qwheres.append('(normalized_id is NULL OR normalized_id = rowid)')
            else:
                qwheres.append('normalized_id = ?')
                qargs.append(normalized)
            q = 'SELECT rowid FROM word WHERE %s' % ' AND '.join(qwheres)
            LOG.debug('query: %s (args: %s)' % (q, qargs))
            cur.execute(q, qargs)

            rows = cur.fetchall()
            if len(rows) > 0:
                return rows[0][0]
            else:
                q = 'INSERT INTO word(previous_id, word, normalized_id) VALUES(?,?,?)'
                qargs = (previous,word,normalized)
                LOG.debug('query: %s (args: %s)' % (q, qargs))
                cur.execute(q, qargs)
                return cur.lastrowid

    def add(self, tokens, emit, expand=lambda words,offset:[]):
        """
        Adds a word to the dictionary.

        :param:tokens: a list of tokens representing the word
        :param:emit: the string to emit if the word is found
        :param:expand: a function which returns an iterator of alternative forms
        """
        if self._con is None:
            self._setup()

        if isinstance(tokens, str):
            tokens = [tokens]

        rowids = []
        for offset in range(len(tokens)):
            tok = tokens[offset]
            previous_rowid = rowids[offset-1] if offset > 0 else None
            rowids.append(self._insertWord(previous_rowid, tok, None))

        for offset in range(len(tokens)):
            previous_rowid = rowids[offset-1] if offset > 0 else None
            for expansion, nwords in expand(tokens, offset):
                previous_expansion_rowid = previous_rowid
                if len(expansion) == 0 or nwords == 0:
                    raise ValueError('lookup expansion requires non-zero arguments')

                for i in range(len(expansion)-1):
                    previous_expansion_rowid = self._insertWord(previous_expansion_rowid, expansion[i], None)

                self._insertWord(previous_expansion_rowid, expansion[-1], rowids[offset-1+nwords])

        with contextlib.closing(self._con.cursor()) as cur:
            q = 'INSERT INTO emit(word_id, emit) VALUES(?,?)'
            args = (rowids[-1], emit)
            cur.execute(q, args)
            self.__tainted = True


class AnnotatorDictionary(Dictionary):
    def add(self, tokens, annotation_type, annotation_features, expand=lambda words,offset:[]):
        return super(AnnotatorDictionary, self).add(tokens, json.dumps({'type':annotation_type, 'features':annotation_features}), expand=expand)


class DictionaryAnnotator(object):
    def __init__(self, dict, close_dictionary=False):
        self.dict = dict
        self._close_dictionary = close_dictionary

    def process(self, doc):
        tokens = sorted(doc.annotations.selectType('token'), key=lambda x:x.span[0])
        states = []
        for tok in tokens:
            states = self.dict._token(tok.features['string'], init_passthru=[], states=states)
            for state in states:
                state.passthru.append(tok)
                if state.emit:
                    emit = json.loads(state.emit)
                    doc.annotations.add(document.Annotation(emit['type'], (state.passthru[0].span[0], state.passthru[-1].span[1]), emit['features']))

    def close(self):
        if self._close_dictionary:
            self.dict.close()
