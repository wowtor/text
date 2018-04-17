from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import logging

from . import document

__metaclass__ = type

LOG = logging.getLogger(__file__)

DEFAULT_SEPARATOR = ' '

class IOBParser():
    stick_left = set(['.', '...', ',', ':', ')'])
    stick_right = set(['('])
    stick_mixed = set(['\'', '"'])
    stick_mixed_count = 0
    linecount = 0
    sentencecount = 0
    chapter = []
    sentence = []
    doc = document.DocumentBuilder()

    def __init__(self, label_column_index, sep=DEFAULT_SEPARATOR, encoding='utf8'):
        self.label_column_index = label_column_index
        self.sep = sep
        self.encoding = encoding

    def endSentence(self):
        if len(self.sentence) > 0:
            self.doc.addAnnotation('sentence', (self.sentence[0].span[0], self.sentence[-1].span[1]), {'seq':self.sentencecount})
        self.sentence = []
        self.sentencecount += 1
        self.stick_mixed_count = 0

    def endChapter(self):
        self.endSentence()
        if len(self.chapter) > 0:
            self.doc.addAnnotation('document', (self.chapter[0].span[0], self.chapter[-1].span[1]), {})
        self.chapter = []

    def parseLine(self, line):
        parts = line.split(self.sep)
        token = parts[0]
        label = parts[self.label_column_index]
        if label.startswith('I-'):
            if self.prev_label is None or self.prev_label[2:] != label[2:]:
                fixlabel = 'B-'+label[2:]
                LOG.warning('label correction: %s -> %s (previous label is %s)' % (label, fixlabel, self.prev_label))
                label = fixlabel
        if token == '-DOCSTART-':
            self.endChapter()
        else:
            if self.prev_token is None or token in self.stick_left:
                pass
            elif self.stick_mixed_count % 2 == 1 and token in self.stick_mixed:  # stick left
                pass
            elif self.stick_mixed_count % 2 == 1 and self.prev_token in self.stick_mixed:  # stick right
                pass
            elif self.prev_token in self.stick_right:
                pass
            else:
                self.doc.addToken(' ')

            if token in self.stick_mixed:
                self.stick_mixed_count += 1

            tok = self.doc.addToken(token, {'label': parts[self.label_column_index]})
            self.sentence.append(tok)

        self.prev_token = token
        self.prev_label = label

    def parseFile(self, path, encoding=None):
        encoding = encoding if encoding is not None else self.encoding
        with open(path, 'rb') as fo:
            return self.parse(codecs.iterdecode(fo, encoding), path=path)

    def parse(self, file, path='unknown'):
        self.path = path
        self.prev_token = None
        self.prev_label = None
        for line in file:
            self.linecount += 1
            line = line.rstrip('\n')
            if line == '':
                self.endSentence()
            else:
                try:
                    self.parseLine(line)
                except Exception as e:
                    raise ValueError('{path}:{lineno}: {msg} (line contents: {line})'.format(path=self.path, lineno=self.linecount, msg=e, line=line))

        self.endChapter()
        self.path = None

        return self.doc.toDocument()


def parse(file, label_column_index, encoding='utf8', sep=DEFAULT_SEPARATOR):
    if isinstance(file, str) or isinstance(file, unicode):
        return IOBParser(label_column_index, sep=sep).parseFile(file, encoding)
    else:
        return IOBParser(label_column_index, sep=sep).parse(file)


class IOBLabel():
    def __init__(self, annotations, label=lambda a: a.type):
        self._annotations = annotations
        self._label = label

    def __call__(self, token):
        for a in self._annotations.selectOffset(*token.span):
            prefix = 'B-' if a.span[0] == token.span[0] else 'I-'
            return prefix + self._label(a)

        return 'O'


class Annotator():
    def __init__(self, name=lambda x: x, features={}):
        self._name = name
        self._features = features

    def createAnnotation(self, etype, first_token, last_token):
        span = (first_token.span[0], last_token.span[1])
        return document.Annotation(self._name(etype), span, self._features)

    def __call__(self, tokens, labels):
        assert len(tokens) == len(labels)
        b_offset = None
        label = None
        for i in range(len(tokens)):
            if b_offset is not None and not labels[i].startswith('I-'):
                yield self.createAnnotation(label, tokens[b_offset], tokens[i-1])
                b_offset = None
                label = None
            if labels[i].startswith('B-'):
                b_offset = i
                label = labels[i][2:]

        if b_offset is not None:
            yield self.createAnnotation(label, tokens[b_offset], tokens[i-1])
