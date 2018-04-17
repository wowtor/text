from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import collections
import enum
import logging

import pycrfsuite

from . import iob

__metaclass__ = type


LOG = logging.getLogger(__file__)


class Mode(enum.Enum):
    TAG = 0
    TRAIN = 1
    TEST = 2


class Ner():
    def __init__(self,
                 mode=Mode.TAG,
                 model=None,
                 features=None,
                 label=lambda x: None,
                 annotator=iob.Annotator(),
                 annotation_key=lambda a: (a.type, a.span[0], a.span[1]),
                 token_types=['token', 'punct'],
                 instance_types=None):
        """Constructor.

        :param mode: training, tagging or testing mode.
        :param model: [TAG, TRAIN, TEST] the filename of the reusable model.
        :param features: [TAG, TRAIN, TEST]
            a feature generator function which accepts two arguments: the token
            sequence and the offset of the current token, and returns an
            iterator over feature key/value pairs.
        :param label: [TRAIN, TEST] a label generator function which accepts a
            token as its single argument and returns the token's label.
        :param annotator: [TAG, TEST] the annotation generator function which
            accepts two arguments: a token list and a label list, and returns
            annotations.
        :param annotation_key: [TEST] a function which accepts an annotation
            as its single argument, and returns the value used for annotation
            comparison.
        :param token_types: [TAG, TRAIN, TEST] a list of annotation types which
            denote tokens.
        :param insatnce_types: [TAG, TRAIN, TEST] a list of annotation types
            which denote instances.
        """
        self._mode = mode
        self._modelfile = model
        self._features = features
        self._label = label
        self._annotator = annotator
        self._annotation_key = annotation_key
        self._token_types = token_types
        self._instance_types = instance_types

    def applyLabels(self, doc, annotator=None):
        if annotator is None:
            annotator = self._annotator
        tokens = sorted(doc.annotations.selectType(*self._token_types), key=lambda x: x.span[0])
        labels = [self._label(tok) for tok in tokens]
        for a in annotator(tokens, labels):
            doc.annotations.add(a)

    def _getInstances(self, doc):
        if self._instance_types is None:
            yield sorted(doc.annotations.selectType(*self._token_types), key=lambda x: x.span[0])
        else:
            ainst = sorted(doc.annotations.selectType(*self._instance_types), key=lambda x: x.span[0])
            atoks = sorted(doc.annotations.selectType(*self._token_types), key=lambda x: x.span[0])
            cursor = 0
            instance = []
            for a in ainst:
                while cursor < len(atoks) and atoks[cursor].span[0] < a.span[1]:
                    instance.append(atoks[cursor])
                    cursor += 1
                yield instance

    def tag(self, doc):
        with pycrfsuite.Tagger().open(self._modelfile) as tagger:
            for tokens in self._getInstances(doc):
                features = [dict(self._features(tokens, i)) for i in range(len(tokens))]
                for a in self._annotator(tokens, tagger.tag(features)):
                    doc.annotations.add(a)

    def train(self, docs):
        try:
            docs = iter(docs)
        except:
            return self.train([docs])

        LOG.info('preparing training data')
        trainer = pycrfsuite.Trainer(verbose=False)
        for doc in docs:
            for tokens in self._getInstances(doc):
                features = [dict(self._features(tokens, i)) for i in range(len(tokens))]
                labels = [self._label(tokens[i]) for i in range(len(tokens))]
                trainer.append(features, labels)
                self._features.update(tokens, labels)

        trainer.set_params({
            'c1': 1.0,   # coefficient for L1 penalty
            'c2': 1e-3,  # coefficient for L2 penalty
            'max_iterations': 50,  # stop earlier
            'feature.possible_transitions': True,  # include transitions that are possible, but not observed
        })

        LOG.info('training')
        trainer.train(self._modelfile)

    def test(self, doc, annotator=None, annotation_key=None):
        if annotation_key is None:
            annotation_key = self._annotation_key
        if annotator is None:
            annotator = self._annotator
        with pycrfsuite.Tagger().open(self._modelfile) as tagger:
            self.entities = set()
            self.predicted = set()
            for tokens in self._getInstances(doc):
                features = [dict(self._features(tokens, i)) for i in range(len(tokens))]
                labels = [self._label(tok) for tok in tokens]
                self.entities.update(annotation_key(e) for e in annotator(tokens, labels))
                self.predicted.update(annotation_key(e) for e in annotator(tokens, tagger.tag(features)))

            for lst in self.entities, self.predicted:
                if None in lst:
                    lst.remove(None)

    def precision(self):
        truepos = len([e for e in self.entities if e in self.predicted])
        falsepos = len([e for e in self.predicted if e not in self.entities])
        if truepos + falsepos == 0:
            return float('NaN')
        return truepos / (truepos + falsepos)

    def recall(self):
        truepos = len([e for e in self.entities if e in self.predicted])
        falseneg = len([e for e in self.entities if e not in self.predicted])
        if truepos + falseneg == 0:
            return float('NaN')
        return truepos / (truepos + falseneg)

    def fscore(self):
        p = self.precision()
        r = self.recall()
        return 2 * p * r / (p + r)

    def writeModelInfo(self, filename):
        with pycrfsuite.Tagger().open(self._modelfile) as tagger:
            info = tagger.info()
            with codecs.open(filename, 'w', encoding='utf8') as f:
                f.write('HEADER\n')
                f.write('======\n')
                for k, v in sorted(info.header.items()):
                    f.write('%s\t%s\n' % (k, v))
                f.write('\n')

                f.write('TRANSITIONS\n')
                f.write('===========\n')
                for (label_from, label_to), weight in collections.Counter(info.transitions).most_common():
                    f.write('%s\t%s\t%.6f\n' % (label_from, label_to, weight))
                f.write('\n')

                f.write('STATE_FEATURES\n')
                f.write('==============\n')
                for (attr, label), weight in collections.Counter(info.state_features).most_common():
                    f.write(u'%.6f\t%s\t%s\n' % (weight, label, attr))

    def process(self, doc):
        return {
            Mode.TAG: self.tag,
            Mode.TRAIN: self.train,
            Mode.TEST: self.test,
        }[self._mode](doc)
