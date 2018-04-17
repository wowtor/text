from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging

from . import document

__metaclass__ = type

LOG = logging.getLogger(__file__)


def serializeDocument(doc):
    jdoc = json.dumps({
        'content': doc.content,
        'annotations': [
            {
                'type': a.type,
                'span': a.span,
                'features': a.features,
            }
            for a in doc.annotations
        ],
        'features': doc.features,
    })
    if doc.source_url is not None:
        jdoc['source_url'] = doc.source_url

    return jdoc


def deserializeDocument(filename=None, fo=None):
    if filename is not None:
        with open(filename, 'rb') as fo:
            return deserializeDocument(fo=fo)

    data = json.load(fo)
    content = data['content']
    source_url = data['source_url']
    features = dict(data['features'].items())
    doc = document.Document(content=content, source_url=source_url, features=features)

    for a in data['annotations']:
        doc.annotations.add(document.Annotation(a['type'], a['span'], dict(a['features'])))

    return doc
