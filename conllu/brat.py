#!/usr/bin/env python

# brat standoff format support.

import re

class Annotation(object):
    """Base class for annotations with ID and type."""

    def __init__(self, id_, type_):
        self.id = id_
        self.type = type_

    def verify_text(self, text):
        """Verify reference text for textbound annotations."""
        pass

    def __unicode__(self):
        raise NotImplementedError
    
    STANDOFF_RE = None

    @classmethod
    def from_standoff(cls, line):
        if cls.STANDOFF_RE is None:
            raise NotImplementedError
        m = cls.STANDOFF_RE.match(line)
        if not m:
            raise ValueError('Failed to parse "%s"' % line)
        return cls(*m.groups())

class Textbound(Annotation):
    """Textbound annotation representing entity mention or event trigger."""

    def __init__(self, id_, type_, spans, text):
        super(Textbound, self).__init__(id_, type_)
        if isinstance(spans, basestring):
            self.spans = Textbound.parse_spans(spans)
        else:
            self.spans = spans
        self.text = text

    def verify_text(self, text):
        offset = 0
        for start, end in self.spans:
            endoff = offset + (end-start)
            assert text[start:end] == self.text[offset:endoff], \
                'Error: text mismatch: "%s" vs. "%s"' % \
                (text[start:end], self.text[offset:endoff])
            offset = endoff + 1

    def __unicode__(self):
        span_str = u';'.join(u'%d %d' % (s[0], s[1]) for s in self.spans)
        return u'%s\t%s %s\t%s' % (self.id, self.type, span_str, self.text)
        
    STANDOFF_RE = re.compile(r'^(\S+)\t(\S+) (\d+ \d+(?:;\d+ \d+)*)\t(.*)$')

    @staticmethod
    def parse_spans(span_string):
        """Return list of (start, end) pairs for given span string."""
        spans = []
        for span in span_string.split(';'):
            start, end = span.split(' ')
            spans.append((int(start), int(end)))
        return spans

class Relation(Annotation):
    """Typed binary relation annotation."""

    def __init__(self, id_, type_, args):
        super(Relation, self).__init__(id_, type_)
        if isinstance(args, basestring):
            self._args = args
        else:
            self._args = ' '.join('%s:%s' % a for a in args)
            
    def args(self):
        a1, a2 = self._args.split(' ')
        a1key, a1val = a1.split(':', 1)
        a2key, a2val = a2.split(':', 1)
        return ((a1key, a1val), (a2key, a2val))

    def __unicode__(self):
        return u'%s\t%s %s' % (self.id, self.type, self._args)
    
    STANDOFF_RE = re.compile(r'^(\S+)\t(\S+) (\S+:\S+ \S+:\S+)$')

class Event(Annotation):
    """Typed, textbound event annotation."""

    def __init__(self, id_, type_, trigger, args):
        super(Event, self).__init__(id_, type_)
        self.trigger = trigger
        self.args = args

    def get_args(self):
        return [a.split(':', 1) for a in self.args.split(' ')]        

    STANDOFF_RE = re.compile(r'^(\S+)\t(\S+):(\S+) (\S+:\S+ ?)*$')

class Normalization(Annotation):
    """Reference relating annotation to external resource."""

    def __init__(self, id_, type_, arg, ref, text):
        super(Normalization, self).__init__(id_, type_)
        self.arg = arg
        self.ref = ref
        self.text = text

    STANDOFF_RE = re.compile(r'^(\S+)\t(\S+) (\S+) (\S+:\S+)\t?(.*)$')

class Attribute(Annotation):
    """Attribute with optional value associated with another annotation."""

    def __init__(self, id_, type_, arg, val):
        super(Attribute, self).__init__(id_, type_)
        self.arg = arg
        self.val = val

    def __unicode__(self):
        if not self.val:
            return '%s\t%s %s' % (self.id, self.type, self.arg)
        else:
            return '%s\t%s %s %s' % (self.id, self.type, self.arg, self.val)

    STANDOFF_RE = re.compile(r'^(\S+)\t(\S+) (\S+) ?(\S*)$')

class Comment(Annotation):
    """Typed free-form text comment associated with another annotation."""

    def __init__(self, id_, type_, arg, text):
        super(Comment, self).__init__(id_, type_)
        self.arg = arg
        self.text = text

    def __unicode__(self):
        return '%s\t%s %s\t%s' % (self.id, self.type, self.arg, self.text)

    STANDOFF_RE = re.compile(r'^(\S+)\t(\S+) (\S+)\t(.*)$')
