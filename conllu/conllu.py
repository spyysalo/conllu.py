#!/usr/bin/env python

# CoNLL-U format support

import re
import codecs

import brat

from itertools import groupby

# feature name-value separator
FSEP = '='
# dependency head-rel separator
DSEP = ':'

# Free-form text annotation type in brat export
COMMENT_TYPE = 'AnnotatorNotes'

class FormatError(Exception):
    def __init__(self, msg, line=None, linenum=None):
        self.msg = msg
        self.line = line
        self.linenum = linenum

    def __str__(self):        
        msg = self.msg
        if self.line is not None:
            msg += ': "'+self.line.encode('ascii', 'replace')+'"'
        if self.linenum is not None:
            msg += ' (line %d)' % self.linenum
        return msg

CPOSTAG_RE = re.compile(r'^[a-zA-Z]+$')
POSTAG_RE = re.compile(r'^[\x20-\xff]+$')

class Element(object):
    """Represents CoNLL-U word or multi-word token."""

    def __init__(self, id_, form, lemma, cpostag, postag,
                 feats, head, deprel, deps, misc, offset=0):
        self.id = id_
        self.form = form
        self.lemma = lemma
        self.cpostag = cpostag
        self.postag = postag
        self._feats = feats
        self.head = head
        self.deprel = deprel
        self._deps = deps
        self.misc = misc

        self.offset = offset
        self.sentence = None

        self.validate()

        self._fmap = None
        self._dlist = None

    def validate(self):
        # minimal format validation (incomplete)

        if not self.is_word():
            # TODO: check multi-word tokens
            return

        # some character set constraints
        if not CPOSTAG_RE.match(self.cpostag):
            raise FormatError('invalid CPOSTAG: %s' % self.cpostag)
        if not POSTAG_RE.match(self.postag):
            raise FormatError('invalid POSTAG: %s' % self.postag)

        # no feature is empty
        if any(True for s in self._feats if len(s) == 0):
            raise FormatError('empty feature: %s' % str(self._feats))

        # feature names and values separated by feature separator
        if any(s for s in self._feats if len(s.split(FSEP)) < 2):
            raise FormatError('invalid features: %s' % str(self._feats))

        # no feature name repeats
        if any(n for n, g in groupby(sorted(s.split(FSEP)[0] for s in self._feats))
               if len(list(g)) > 1):
            raise FormatError('duplicate features: %s' % str(self._feats))

        # head is integer
        try:
            int(self.head)
        except ValueError:
            raise FormatError('non-int head: %s' % self.head)

    def is_word(self):
        try:
            val = int(self.id)
            return True
        except ValueError:
            return False

    def has_feat(self, name):
        return name in self.feat_map()

    def add_feats(self, feats):
        # name-value pairs
        assert not any(nv for nv in feats if len(nv) != 2)
        self._feats.extend(FSEP.join(nv) for nv in feats)
        self._fmap = None

    def set_feats(self, feats):
        self._feats = []
        self.add_feats(feats)
        self._fmap = None

    def remove_feat(self, name, value):
        nv = FSEP.join((name, value))
        self._feats.remove(nv)
        self._fmap = None

    def append_misc(self, value):
        if self.misc == '_':
            self.misc = value
        else:
            self.misc = self.misc + '|' + value

    def feat_names(self):
        return [f.split(FSEP)[0] for f in self._feats]

    def feat_map(self):
        if self._fmap is None:
            try:
                self._fmap = dict([f.split(FSEP, 1) for f in self._feats])
            except ValueError:
                raise ValueError('failed to convert ' + str(self._feats))
        return self._fmap

    def feats(self):
        return self.feat_map().items()

    def deps(self, include_primary=False):
        if self._dlist is None:
            try:
                self._dlist = [d.split(DSEP, 1) for d in self._deps]
            except:
                raise FormatError('failed to parse ' + str(self._deps))
        if not include_primary:
            return self._dlist
        else:
            return [(self.head, self.deprel)] + self._dlist

    def set_deps(self, dlist):
        self._deps = [DSEP.join(hd) for hd in dlist]
        self._dlist = None

    def has_deprel(self, deprel, check_deps=True):
        if self.deprel == deprel:
            return True
        elif not check_deps:
            return False
        elif any(d for d in self.deps() if d[1] == deprel):
            return True
        else:
            return False

    def wipe_annotation(self):
        self.lemma = '_'
        self.cpostag = '_'
        self.postag = '_'
        self._feats = '_'
        self.head = '_'
        self.deprel = '_'
        self._deps = '_'
        self.misc = '_'

    def to_brat_standoff(self, element_by_id):
        """Return list of brat standoff annotations for the element."""
        # base ID, unique within the document
        bid = '%s.%s' % (self.sentence.id, self.id)
        if self.is_word():
            # Word, maps to: Textbound with the coarse POS tag as
            # type, freeform text comment with LEMMA, POSTAG and
            # MISC (when nonempty) as values, attribute for each
            # feature.
            # textbounds
            spans = [[self.offset, self.offset+len(self.form)]]
            textbounds = [
                brat.Textbound('T'+bid, self.cpostag, spans, self.form),
            ]
            # comments
            freeform = [
                ('LEMMA', self.lemma),
                ('POSTAG', self.postag),
            ]
            if self.misc != '_':
                freeform.append(('MISC', self.misc))
            comments = [
                brat.Comment('#'+bid, COMMENT_TYPE, 'T'+bid,
                             ' '.join(u'%s=%s' % f for f in freeform))
            ]
            # attributes
            attribs = []
            for name, value in self.feats():
                aid = 'A'+bid+'-%d'%(len(attribs)+1)
                attribs.append(brat.Attribute(aid, name, 'T'+bid, value))
            # relations
            relations = []
            for head, deprel in self.deps(include_primary=True):
                if head == '0':
                    continue # skip root
                rid = 'R'+bid+'-%d'%(len(relations)+1)
                tid = '%s.%s' % (self.sentence.id, element_by_id[head].id)
                args = [('Arg1', 'T'+tid), ('Arg2', 'T'+bid)]
                relations.append(brat.Relation(rid, deprel, args))
            return textbounds + attribs + relations + comments
        else:
            # Multi-word token, maps to: Textbound with a special type,
            # and free-text comment containing the form.
            # Span corresponds to maximum span over covered tokens.
            start, end = self.id.split('-')
            first, last = element_by_id[start], element_by_id[end]
            spans = [[first.offset, last.offset+len(last.form)]]
            text  = ' '.join(str(element_by_id[str(t)].form)
                              for t in range(int(start), int(end)+1))
            return [
                brat.Textbound('T'+bid, 'Multiword-token', spans, text),
                brat.Comment('#'+bid, COMMENT_TYPE, 'T'+bid, 'FORM='+self.form)
            ]

    def __unicode__(self):
        fields = [self.id, self.form, self.lemma, self.cpostag, self.postag, 
                  self._feats, self.head, self.deprel, self._deps, self.misc]
        fields[5] = '_' if fields[5] == [] else '|'.join(sorted(fields[5], key=lambda s: s.lower())) # feats
        fields[8] = '_' if fields[8] == [] else '|'.join(fields[8]) # deps
        return '\t'.join(fields)

    @classmethod
    def from_string(cls, s):
        fields = s.split('\t')
        if len(fields) != 10:
            raise FormatError('got %d/10 field(s)' % len(fields), s)
        fields[5] = [] if fields[5] == '_' else fields[5].split('|') # feats
        fields[8] = [] if fields[8] == '_' else fields[8].split('|') # deps
        return cls(*fields)

class Sentence(object):
    def __init__(self, id_=0, filename=None, base_offset=0):
        """Initialize a new, empty Sentence."""
        self.comments = []
        self._elements = []
        self.id = id_
        self.filename = filename
        self.base_offset = base_offset
        self.next_offset = base_offset
        # mapping from IDs to elements
        self._element_by_id = None

    def append(self, element):
        """Append word or multi-word token to sentence."""
        self._elements.append(element)
        assert element.sentence is None, 'element in multiple sentences?'
        element.sentence = self
        element.offset = self.next_offset
        if element.is_word():
            self.next_offset += len(element.form) + 1
        else:
            # multi-word token; don't shift position of next token
            pass
        # reset cache (TODO: extend instead)
        self._element_by_id = None

    def empty(self):
        return self._elements == []

    def words(self):
        """Return a list of the words in the sentence."""
        return [e for e in self._elements if e.is_word()]

    def text(self, use_tokens=False, separator=' '):
        """Return the text of the sentence."""
        if use_tokens:
            raise NotImplementedError('multi-word token text not supported.')
        else:
            return separator.join(w.form for w in self.words())

    def length(self, use_tokens=False):
        """Return the length of the sentence text."""
        return len(self.text(use_tokens))

    def element_by_id(self):
        """Return mapping from id to element."""
        if self._element_by_id is None:
            self._element_by_id = { e.id: e for e in self._elements }
        return self._element_by_id

    def get_element(self, id_):
        """Return element by id."""
        return self.element_by_id()[id_]

    def wipe_annotation(self):
        for e in self._elements:
            if e.is_word():
                e.wipe_annotation()

    def remove_element(self, id_):
        # TODO: implement for cases where multi-word tokens span the
        # element to remove.
        assert len(self.words()) == len(self._elements), 'not implemented'

        # there must not be references to the element to remove
        for w in self.words():
            assert not any(h for h, d in w.deps(True) if h == id_), \
                'cannot remove %s, references remain' % id_

        # drop element
        element = self.get_element(id_)
        self._elements.remove(element)
        self._element_by_id = None

        # update IDs
        id_map = { u'0' : u'0' }
        for i, w in enumerate(self.words()):
            new_id = unicode(i+1)
            id_map[w.id] = new_id
            w.id = new_id
        for w in self.words():
            w.head = id_map[w.head]
            w.set_deps([(id_map[h], d) for h, d in w.deps()])

    def dependents(self, head, include_secondary=True):
        if isinstance(head, Element):
            head_id = head.id

        deps = []
        for w in self.words():
            if not include_secondary:
                wdeps = [(w.head, w.deprel)]
            else:
                wdeps = w.deps(include_primary=True)
            for head, deprel in wdeps:
                if head == head_id:
                    deps.append((w.id, deprel))
        return deps

    def assign_offsets(self, base_offset=None, use_tokens=False):
        """Assign offsets to sentence elements."""
        if base_offset is not None:
            self.base_offset = base_offset
        offset = self.base_offset
        if use_tokens:
            raise NotImplementedError('multi-word token text not supported.')
        else:
            # Words are separated by a single character and multi-word
            # tokens appear at the start of the position of their
            # initial words with zero-width spans.
            for e in self._elements:
                e.offset = offset
                if e.is_word():
                    offset += len(e.form) + 1

    def to_brat_standoff(self):
        """Return list of brat standoff annotations for the sentence."""
        # Create mapping from ID to element.
        annotations = []
        for element in self._elements:
            annotations.extend(element.to_brat_standoff(self.element_by_id()))
        return annotations

    def __unicode__(self):
        element_unicode = [unicode(e) for e in self._elements]
        return '\n'.join(self.comments + element_unicode)+'\n'

class Document(object):
    def __init__(self, filename=None):
        self._sentences = []
        self.filename = filename

    def append(self, sentence):
        """Append sentence to document."""
        self._sentences.append(sentence)

    def empty(self):
        return self._sentences == []

    def words(self):
        """Return a list of the words in the document."""
        return [w for s in self.sentences() for w in s.words()]

    def sentences(self):
        """Return a list of the sentences in the document."""
        return self._sentences

    def text(self, use_tokens=False, element_separator=' ',
             sentence_separator='\n'):
        return sentence_separator.join(s.text(use_tokens, element_separator)
                                       for s in self.sentences())

    def to_brat_standoff(self):
        """Return list of brat standoff annotations for the document."""
        annotations = []
        for sentence in self._sentences:
            annotations.extend(sentence.to_brat_standoff())
        return annotations

def _file_name(file_like, default='document'):
    """Return name of named file or file-like object, or default if not
    available."""
    # If given a string, assume that it's the name
    if isinstance(file_like, basestring):
        return file_like
    try:
        return file_like.name
    except AttributeError:
        return default

def read_documents(source, filename=None):
    """Read CoNLL-U format, yielding Document objects."""

    if filename is None:
        filename = _file_name(source)
    current = Document(filename)
    for sentence in read_conllu(source, filename):
        # TODO: recognize and respect document boundaries in source data.
        current.append(sentence)
    yield current

def read_conllu(source, filename=None):
    """Read CoNLL-U format, yielding Sentence objects.

    Note: incomplete implementation, lacks validation."""

    # If given a string, assume it's a file name, open and recurse.
    if isinstance(source, basestring):
        with codecs.open(source, encoding='utf-8') as i:
            for s in read_conllu(i, filename=source):
                yield s
        return

    if filename is None:
        filename = _file_name(source)

    sent_num, offset = 1, 0
    current = Sentence(sent_num, filename, offset)
    for ln, line in enumerate(source):
        line = line.rstrip('\n')
        if not line:
            if not current.empty():
                # Assume single character sentence separator.
                offset += current.length() + 1
                yield current
            else:
                raise FormatError('empty sentence', line, ln+1)
            sent_num += 1
            current = Sentence(sent_num, filename, offset)
        elif line[0] == '#':
            current.comments.append(line)
        else:
            try:
                current.append(Element.from_string(line))
            except FormatError, e:
                e.linenum = ln+1
                raise e
    assert current.empty(), 'missing terminating whitespace'
