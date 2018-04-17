from __future__ import absolute_import, division, print_function, unicode_literals

import bisect
import collections
import io
import logging
import re
import xml.sax.saxutils


__metaclass__ = type

LOG = logging.getLogger(__file__)


class Annotation():
    def __init__(self, type, span, features={}):
        self.type = type
        self.span = span
        self.features = features


class AnnotationSet():
    def __init__(self, document):
        self.document = document
        self.key = lambda a:a.span[0]
        self._all = []
        self._all_keys = []
        self.by_type = collections.defaultdict(list)
        self.by_type_keys = collections.defaultdict(list)

    def __iter__(self):
        return iter(self._all)

    def __len__(self):
        return len(self._all)

    def __getitem__(self, index):
        return self._all[index]

    def add(self, annotation):
        """
        Adds an annotation to this annotation set.

        :param annotation: an annotation object
        :return: the added annotation object
        """
        key = self.key(annotation)

        index = bisect.bisect(self._all_keys, key)
        self._all.insert(index, annotation)
        self._all_keys.insert(index, key)

        index = bisect.bisect(self.by_type_keys[annotation.type], key)
        self.by_type[annotation.type].insert(index, annotation)
        self.by_type_keys[annotation.type].insert(index, key)

        return annotation

    def selectType(self, *types):
        """
        Returns the subset of annotations whose type matches the argument.

        :param types: the included annotation types
        :return: an AnnotationSet which contains only a subset of annotation types
        """
        set = AnnotationSet(self.document)
        for type in types:
            if type in self.by_type:
                set.by_type[type].extend(self.by_type[type])
                set.by_type_keys[type].extend(self.by_type_keys[type])
        for i in range(len(self._all)):
            if self._all[i].type in types:
                set._all.append(self._all[i])
                set._all_keys.append(self._all_keys[i])
        return set

    def selectOffset(self, offset_from, offset_to):
        """
        Returns the subset of annotations which touch the specified range.

        :param offset_from: the character offset of the beginning of the range (inclusive)
        :param offset_to: the character offset of the end of the range (exclusive)
        :return: an AnnotationSet which contains only annotations which cover (part of) the selected range
        """
        set = AnnotationSet(self.document)
        index = bisect.bisect_left(self._all_keys, offset_from)
        while index > 0 and self._all[index-1].span[1] > offset_from:
            index -= 1

        while index < len(self._all) and self._all[index].span[0] < offset_to:
            set.add(self._all[index])
            index += 1

        return set


class Document():
    def __init__(self, content, source_url=None, annotations=[], features={}):
        self.source_url = source_url
        self.content = content
        self.features = features
        self.annotations = AnnotationSet(self)

        for a in annotations:
            self.annotations.add(a)

    def toJson(self):
        from . import json
        return json.serializeDocument(self)


class DocumentBuilder():
    def __init__(self):
        self.size = 0
        self.content = io.StringIO()
        self.annotations = []
        self.features = {}

    def addToken(self, token, extra_features={}):
        if re.match('[\s]+', token):
            type = 'space'
        elif re.search('[a-zA-Z0-9]+', token):
            type = 'token'
        else:
            type = 'punct'

        features = {'string': token}
        features.update(extra_features)
        return self.addPart(type, token, features)

    def addPart(self, type, text, features):
        self.content.write(text)
        self.size += len(text)
        return self.addAnnotation(type, (self.size-len(text), self.size), features)

    def addAnnotation(self, type, span, features={}):
        a = Annotation(type, span, features)
        self.annotations.append(a)
        return a

    def toDocument(self):
        return Document(self.content.getvalue(), annotations=self.annotations, features=self.features)


def fromText(file):
    if isinstance(file, str):
        with open(file, 'rb') as fo:
            return fromText(fo)

    doc = DocumentBuilder()
    pages = file.read().split(b'\x0c')
    for i in range(len(pages)):
        doc.addPart('page', pages[i].decode('utf8')+'\n', {'seq':i+1})
    return doc.toDocument()


class Pipeline():
    def __init__(self, processors=None):
        self.processors = processors if processors is not None else []

    def append(self, processor):
        self.processors.append(processor)

    def process(self, doc):
        for p in self.processors:
            p.process(doc)
