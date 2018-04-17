#!/usr/bin/env python

import argparse
import logging
import sys

import text
import text.ner


DOCUMENT_FILENAME = 'example.json'

LOG = logging.getLogger(__file__)


class Tagger:
    def __init__(self, modelfile, parser):
        self._modelfile = modelfile
        self._parser = parser

        fg = text.features.AggregatedFeatureGenerator(
                text.features.PriorFeatureGenerator(),
                #text.features.OffsetFeatureGenerator([0,-1]),
                text.features.LengthFeatureGenerator(),
                text.features.BigramFeatureGenerator(text.features.TokenFeatureGenerator()),
                text.features.WindowFeatureGenerator(text.features.OrthographicFeatureGenerator(), range(-2, 3)),
                text.features.WindowFeatureGenerator(text.features.TokenFeatureGenerator(), range(-2, 3)),
                text.features.PreviousMapFeatureGenerator(),
            )
        fg = text.features.StoreFeatureGenerator(fg)
        self._fg = fg

        # instantiate the NER
        self._namefinder = text.ner.Ner(
            model=modelfile,  # the NER model filename
            features=fg,  # a feature generator function
            label=lambda x:x.features['label'],  # a function to map tokens to labels
        )

    def train(self, datafiles):
        trainingset = (self._parser.parseFile(filename) for filename in datafiles)
        self._namefinder.train(trainingset)

        model_info_filename = self._modelfile + '.txt'
        LOG.info('writing model info to ' + model_info_filename)
        self._namefinder.writeModelInfo(model_info_filename)

    def test(self, datafiles):
        for filename in datafiles:
            testdoc = self._parser.parseFile(filename)
            for e in ['PER', 'ORG', 'LOC', 'MISC']:
                self._namefinder.test(testdoc, annotation_key=lambda a:(a.type, a.span[0], a.span[1]) if a.type==e else None)
                print('%s: %s: f: %.2f; p: %.2f; r: %.2f' % (filename, e, self._namefinder.fscore(), self._namefinder.precision(), self._namefinder.recall()))

    def tag(self, filenames, tag_format):
        for filename in filenames:
            tagdoc = self._parser.parseFile(filename)
            self._namefinder.tag(tagdoc)

            f = sys.stdout
            if tag_format == 'json':
                f.write(tagdoc.toJson())
            elif tag_format == 'list':
                for a in tagdoc.annotations:
                    if a.type in ['PER', 'ORG', 'LOC', 'MISC']:
                        f.write('{type}\t{span0}:{span1}\t{form}\n'.format(type=a.type, span0=a.span[0], span1=a.span[1], form=tagdoc.content[a.span[0]:a.span[1]]))


class TextParser:
    def parseFile(self, filename):
        with open(filename, 'rt') as f:
            doc = text.Document(f.read())
        text.tokenizer.Tokenizer().process(doc)

        return doc


if __name__ == '__main__':
    parser = argparse.ArgumentParser('text')
    parser.add_argument('-v', action='count', default=0, help='increase verbosity')
    parser.add_argument('-q', action='count', default=0, help='decrease verbosity')
    parser.add_argument('--model', metavar='FILE', default='ner.bin', help='write/read the model from FILE')
    parser.add_argument('--train', nargs='+', metavar='FILE', help='training mode -- arguments are IOB formatted files')
    parser.add_argument('--test', nargs='+', metavar='FILE', help='test mode -- arguments are IOB formatted files')
    parser.add_argument('--tag', nargs='+', metavar='FILE', help='tagging mode -- arguments are UTF8 encoded text files')
    parser.add_argument('--input-format', metavar='FORMAT', default='conll', help='use STYLE when parsing input files (sonar|conll|text)')
    parser.add_argument('--output-format', metavar='STYLE', default='list', help='use STYLE when producing tagged output files (list|json)')
    args = parser.parse_args()

    loglevel = min(logging.CRITICAL, max(logging.DEBUG, logging.INFO + (args.v - args.q)*10))
    logging.basicConfig(level=loglevel)

    if args.input_format == 'conll':
        parser = text.iob.IOBParser(2, sep=' ', encoding='latin1')
    elif args.input_format == 'sonar':
        parser = text.iob.IOBParser(1, sep='\t', encoding='utf8')
    elif args.input_format == 'text':
        parser = TextParser()
    else:
        print('Illegal argument: %s' % args.iob_format)
        parser.print_help()
        sys.exit(1)

    tagger = Tagger(args.model, parser=parser)

    if args.train:
        LOG.info('training')
        tagger.train(args.train)
    if args.test:
        LOG.info('testing')
        tagger.test(args.test)
    if args.tag:
        LOG.info('tagging')
        tagger.tag(args.tag, tag_format=args.output_format)
