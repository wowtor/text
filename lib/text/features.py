from __future__ import absolute_import, division, print_function, unicode_literals

import string


TOKEN_STRING = lambda x:x.features['string'].lower()

__metaclass__ = type


class FeatureGenerator():
    def __call__(self, token_sequence, index):
        raise ValueError('not implemented')

    def reset(self):
        pass

    def update(self, tokens, outcomes):
        pass


class ProxyFeatureGenerator():
    def __init__(self, backend):
        self.backend = backend

    def reset(self):
        self.backend.reset()

    def update(self, tokens, outcomes):
        self.backend.update(tokens, outcomes)


def decode(k, v):
    if isinstance(k, bytes):
        k = k.decode('utf8')
    if isinstance(v, bytes):
        v = v.decode('utf8')
    return k, v


class StoreFeatureGenerator(ProxyFeatureGenerator):
    def __init__(self, backend):
        super(StoreFeatureGenerator, self).__init__(backend)

    def __call__(self, token_sequence, index):
        features = list(self.backend(token_sequence, index))
        token_sequence[index].features['features'] = [decode(k,v) for k,v in features]
        return features


class AggregatedFeatureGenerator():
    def __init__(self, *backend):
        self.backend = backend

    def __call__(self, token_sequence, index):
        for fg in self.backend:
            # TODO: yield from
            for item in fg(token_sequence, index):
                # TODO: inefficient
                item = list(item)
                for i in range(len(item)):
                    if isinstance(item[i], str):
                        item[i] = item[i].encode('utf8')
                yield item

    def reset(self):
        for fg in self.backend:
            fg.reset()

    def update(self, tokens, outcomes):
        for fg in self.backend:
            fg.update(tokens, outcomes)


class PriorFeatureGenerator(FeatureGenerator):
    def __call__(self, token_sequence, index):
        yield 'prior', 1


class BigramFeatureGenerator(ProxyFeatureGenerator):
    def __init__(self, backend):
        super(BigramFeatureGenerator, self).__init__(backend)

    def __call__(self, token_sequence, index):
        wflist = list(self.backend(token_sequence, index))
        if index > 0:
            for pfname, pfvalue in self.backend(token_sequence, index-1):
                for wfname, wfvalue in wflist:
                    yield 'p%s,%s' % (pfname, wfname), '%s,%s' % (pfvalue, wfvalue)
        if index+1 < len(token_sequence):
            for nfname, nfvalue in self.backend(token_sequence, index+1):
                for wfname, wfvalue in wflist:
                    yield '%s,n%s' % (wfname, nfname), '%s,%s' % (wfvalue, nfvalue)


class OffsetFeatureGenerator(FeatureGenerator):
    def __init__(self, offsets=[0,1,-1,-2]):
        self._pos = [p for p in offsets if p >= 0]
        self._neg = [p for p in offsets if p < 0]

    def __call__(self, token_sequence, index):
        if index in self._pos:
            yield 'pos%d' % index, 1
        if index - len(token_sequence) in self._neg:
            yield 'pos%d' % (index - len(token_sequence)), 1


class LengthFeatureGenerator(FeatureGenerator):
    def __init__(self, filter=TOKEN_STRING):
        self._filter = filter

    def __call__(self, token_sequence, index):
        yield 'len', str(len(self._filter(token_sequence[index])))


class OrthographicFeatureGenerator(FeatureGenerator):
    _punctuation = set(string.punctuation)

    def __init__(self, filter=TOKEN_STRING):
        self._filter = filter

    def __call__(self, token_sequence, index):
        s = self._filter(token_sequence[index])
        punctlen = len([ ch for ch in s if ch in self._punctuation ])
        if s.isdigit():
            yield 'orth', 'digit'
        elif s.isalpha():
            yield 'orth', 'alpha'
            if s.isupper():
                yield 'orth', 'upper'
            if s.islower():
                yield 'orth', 'lower'
            if s.istitle():
                yield 'orth', 'title'
        elif s.isspace():
            yield 'orth', 'space'
        elif s.isalnum():
            yield 'orth', 'alnum'
        elif punctlen == len(s):
            yield 'orth', 'punct'
        else:
            yield 'orth', 'other'


class PreviousMapFeatureGenerator():
    def __init__(self, filter=TOKEN_STRING):
        self._filter = filter
        self.reset()

    def __call__(self, token_sequence, index):
        s = self._filter(token_sequence[index])
        if s in self._outcomes:
            yield 'pd', self._outcomes[s]

    def reset(self):
        self._outcomes = {}

    def update(self, tokens, outcomes):
        for i in range(len(tokens)):
            s = self._filter(tokens[i])
            self._outcomes[s] = outcomes[i]


class TokenFeatureGenerator(FeatureGenerator):
    def __init__(self, filter=TOKEN_STRING):
        self._filter = filter

    def __call__(self, token_sequence, index):
        yield 'w', self._filter(token_sequence[index])


class WindowFeatureGenerator(ProxyFeatureGenerator):
    def __init__(self, backend, window):
        """
        Instantiates a window feature generator with the specified backend and window.

        :param backend: another feature generator which is called for each token within the window of this FG
        :param window: a list of offsets which specifies the window, relative to a current token
        """
        super(WindowFeatureGenerator, self).__init__(backend)
        self.window = window

    def __call__(self, token_sequence, index):
        for offset in self.window:
            if index+offset >= 0 and index+offset < len(token_sequence):
                for name, value in self.backend(token_sequence, index+offset):
                    yield '%s[%d]' % (name, offset), value
