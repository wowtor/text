from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import io
import logging
import xml.sax.saxutils


__metaclass__ = type

LOG = logging.getLogger(__file__)


GateValue = collections.namedtuple('GateValue', ['value', 'class_name', 'item_class_name'])
JAVA_TYPES = {
    str: 'java.lang.String',
    int: 'java.lang.Integer',
    float: 'java.lang.Float',
}
try:
    JAVA_TYPES[unicode] = 'java.lang.String'
except NameError:
    pass


def xmlescape(s):
    return xml.sax.saxutils.escape(s, entities={'\n': '&#10;', '\x0c': '&#10;', '\x09': '&#09;'})


def toGateXML(doc):
    fo = io.StringIO()
    fo.write('<GateDocument version="3">\n')
    fo.write('<GateDocumentFeatures>\n')
    if doc.document.source_url is not None:
        fo.write(
            '  <Feature><Name className="java.lang.String">gate.SourceURL</Name><Value className="java.lang.String">%s</Value></Feature>\n' % xmlescape(
                doc.document.source_url))
    fo.write('</GateDocumentFeatures>\n')

    fo.write('<TextWithNodes>')
    nodes = set()
    nodes.add(0)
    nodes.add(len(doc.document.content))
    for a in doc._all:
        nodes.add(a.span[0])
        nodes.add(a.span[1])
    offset = 0
    for n in sorted(list(nodes)):
        fo.write(xml.sax.saxutils.escape(doc.document.content[offset:n], entities={'\x0c': '&#10;'}))
        offset = n
        fo.write('<Node id="%d"/>' % n)
    fo.write('</TextWithNodes>')

    fo.write('<AnnotationSet>\n')
    count = 0
    for a in doc._all:
        fo.write('  <Annotation Id="%d" Type="%s" StartNode="%d" EndNode="%d">\n' % (
        count, xmlescape(a.type), a.span[0], a.span[1]))
        for k, v in a.features.items():
            gv = toGateValue(v)
            itemclassattr = '' if gv.item_class_name is None else ' itemClassName="%s"' % gv.item_class_name
            fo.write(
                '    <Feature><Name className="java.lang.String">%s</Name><Value className="%s"%s>%s</Value></Feature>\n' % (
                xmlescape(k), gv.class_name, itemclassattr, xmlescape(gv.value)))
        fo.write('  </Annotation>\n')
        count += 1
    fo.write('</AnnotationSet>\n')
    fo.write('</GateDocument>')
    return fo.getvalue()


def toGateValue(v):
    if type(v) in JAVA_TYPES:
        return GateValue(v, JAVA_TYPES[type(v)], None)
    if isinstance(v, list):
        if len(v) == 0:
            item_class_name = None
        else:
            itemvalue = toGateValue(v[0])
            item_class_name = itemvalue.class_name
        return GateValue(';'.join([str(i) for i in v]), 'java.lang.ArrayList', item_class_name)

    raise ValueError('unrecognized type: %s' % type(v))


def toInline(doc):
    a_start = sorted(doc._all, key=lambda x: (x.span[0], -x.span[1], x.type))
    a_end = sorted(doc._all, key=lambda x: (-x.span[1], x.span[0], x.type), reverse=True)
    i_start = 0
    i_end = 0
    offset = 0
    stack = set()
    result = io.StringIO()
    while offset < len(doc.document.content) or i_start < len(a_start) or i_end < len(a_end):
        pos = min(a_start[i_start].span[0] if i_start < len(a_start) else len(doc.document.content),
                  a_end[i_end].span[1] if i_end < len(a_end) else len(doc.document.content))
        result.write(xml.sax.saxutils.escape(doc.document.content[offset:pos]))
        offset = pos
        if i_end < len(a_end) and a_end[i_end] in stack and a_end[i_end].span[1] == offset:
            result.write('</%s>' % a_end[i_end].type)
            stack.remove(a_end[i_end])
            i_end += 1
        elif i_start < len(a_start) and a_start[i_start].span[0] == offset:
            result.write('<%s%s>' % (a_start[i_start].type, ''.join(
                ' %s="%s"' % (k, xmlescape(toGateValue(v).value)) for k, v in a_start[i_start].features.items())))
            stack.add(a_start[i_start])
            i_start += 1

    return result.getvalue()
