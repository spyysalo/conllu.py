#!/usr/bin/env python

# Convert to and from CoNLL-U format.

import os
import sys
import codecs

from conllu import conllu

def argparser():
    import argparse
    parser = argparse.ArgumentParser(description="Convert CoNLL-U data.")
    parser.add_argument('-o', '--output', metavar='DIR', default=None,
                        help='Output directory.')
    parser.add_argument('file', nargs='+', help='Source file(s).')
    return parser

def output_document_text(document, output, options=None):
    print >> output, document.text()

def output_document_annotations(document, output, options=None):
    for annotation in document.to_brat_standoff():
        print >> output, unicode(annotation)
    
def output_document(document, options=None):
    """Output given document according to given options."""
    if options is None or options.output is None:
        # If no output directory is specified, output both to stdout
        output_document_text(document, sys.stdout, options)
        output_document_annotations(document, sys.stdout, options)
    else:
        basefn = os.path.splitext(os.path.basename(document.filename))[0]
        txtfn = os.path.join(options.output, basefn+'.txt')
        annfn = os.path.join(options.output, basefn+'.ann')
        with codecs.open(txtfn, 'wt', encoding='utf-8') as txtout:
            output_document_text(document, txtout, options)
        with codecs.open(annfn, 'wt', encoding='utf-8') as annout:
            output_document_annotations(document, annout, options)

def convert(source, options=None):
    # TODO: support conversions other than CoNLL-U to brat.
    for document in conllu.read_documents(source):
        output_document(document, options)
    
def main(argv):
    args = argparser().parse_args(argv[1:])
    for fn in args.file:
        convert(fn, args)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
