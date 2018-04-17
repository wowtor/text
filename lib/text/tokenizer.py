import itertools
import re

from . import document


SPACEPTN = r' \t\n\r'
WORDPTN = r'a-zA-Z0-9'
CTRLPTN = re.escape(''.join(map(chr, itertools.chain(range(0,8), [11,12], range(14,32), range(127,160)))))


def mktype(chars):
    return re.compile(r'(^|(?<![%s]))([%s]+)($|(?![%s]))' % ((chars,)*3))


TYPES = [(cls, type, mktype(chars)) for cls, type, chars in [
    ('space', 'control', CTRLPTN),
    ('space', 'space', SPACEPTN),
    ('token', 'alnum', WORDPTN),
    ('punct', 'punct', '^' + SPACEPTN + WORDPTN + CTRLPTN),
]]


class Tokenizer(object):
    def process(self, doc):
        for cls, type, regex in TYPES:
            for m in regex.finditer(doc.content):
                doc.annotations.add(document.Annotation(cls, (m.start(2), m.end(2)), {'string':m.group(2)}))
