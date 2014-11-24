#!/usr/bin/env python

# CoNLL-U format support

from collections import namedtuple

class FormatError(Exception):
    def __init__(self, msg, line=None, linenum=None):
        self.msg = msg
        self.line = line
        self.linenum = linenum

    def __str__(self):        
        msg = self.msg
        if self.line is not None:
            msg += ' "'+self.line.encode('ascii', 'replace')+'"'
        if self.linenum is not None:
            msg += ' (line %d)' % self.linenum
        return msg

class Element(object):
    def __init__(self, id_, form, lemma, cpostag, postag,
                 feats, head, deprel, deps, misc):
        self.id = id_
        self.form = form
        self.lemma = lemma
        self.cpostag = cpostag
        self.postag = postag
        self.feats = feats
        self.head = head
        self.deprel = deprel
        self.deps = deps
        self.misc = misc

        # basic sanity: feature names and values separated by equals sign
        assert not any(s for s in self.feats if len(s.split('=')) < 2), \
            'invalid features: %s' % str(self.feats)

    def is_word(self):
        try:
            val = int(self.id)
            return True
        except ValueError:
            return False

    def feat_names(self):
        return [f.split('=')[0] for f in self.feats]

    def feat_map(self):
        try:
            return dict([f.split('=', 1) for f in self.feats])
        except ValueError:
            raise ValueError('failed to convert ' + str(self.feats))

    def __unicode__(self):
        fields = [self.id, self.form, self.lemma, self.cpostag, self.postag, 
                  self.feats, self.head, self.deprel, self.deps, self.misc]
        fields[5] = '_' if fields[5] == [] else '|'.join(fields[5]) # feats
        fields[8] = '_' if fields[8] == [] else '|'.join(fields[8]) # deps
        return '\t'.join(fields)

    @classmethod
    def from_string(cls, s):
        fields = s.split('\t')
        if len(fields) != 10:
            raise FormatError('%d fields' % len(fields), s)
        fields[5] = [] if fields[5] == '_' else fields[5].split('|') # feats
        fields[8] = [] if fields[8] == '_' else fields[8].split('|') # deps
        return cls(*fields)

class Sentence(object):
    def __init__(self):
        self.comments = []
        self.elements = []

    def words(self):
        return [e for e in self.elements if e.is_word()]

    def __unicode__(self):
        element_unicode = [unicode(e) for e in self.elements]
        return '\n'.join(self.comments + element_unicode)+'\n'

def read_conllu(f):
    '''Read CoNLL-U format, yielding Sentence objects.

    Note: incomplete implementation, lacks validation.'''

    current = Sentence()

    for ln, line in enumerate(f):
        line = line.rstrip('\n')
        if not line:
            yield current
            current = Sentence()
        elif line[0] == '#':
            current.comments.append(line)
        else:
            try:
                current.elements.append(Element.from_string(line))
            except FormatError, e:
                e.linenum = ln+1
                raise e
    assert not current.elements
