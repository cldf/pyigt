"""
Support for parsing the notation for morpheme/gloss structure proposed by the
Leipzig Glossing Rules.
"""
import re
import unicodedata

import attr

from pyigt.util import is_standard_abbr

__all__ = [
    # Types of morpheme gloss elements:
    'GlossElement', 'Infix', 'GlossElementAfterSemicolon', 'GlossElementAfterColon',
    'GlossElementAfterBackslash', 'PatientlikeArgument', 'NonovertElement', 'InherentCategory',
    # Types of morphemes:
    'Morpheme', 'MorphemeAfterEquals', 'MorphemeAfterTilde', 'MORPHEME_SEPARATORS',
    'split_morphemes',
    # Wrapper
    'GlossedWord',
]


class GlossElement(str):
    """
    Rule 4. Gloss elements are separated by ".".
    """
    start = '.'
    end = None
    in_gloss_only = True

    def __init__(self, s):
        self.prev = None
        self.next = None

    def __repr__(self):
        return '<{} "{}">'.format(
            self.__class__.__name__, self.encode('ascii', 'replace').decode())

    @property
    def is_agentlike_argument(self):
        return isinstance(self.next, PatientlikeArgument)

    @property
    def is_standard_abbreviation(self):
        return is_standard_abbr(self)

    @property
    def is_category_label(self):
        return re.fullmatch('[A-Z0-9]+', self)


class Infix(GlossElement, str):
    """
    Rule 9. Infixes are enclosed in angle brackets.
    """
    start = '<'
    end = '>'
    in_gloss_only = False


class GlossElementAfterSemicolon(GlossElement):
    """
    Rule 4B. Distinct gloss elements can be separated by ";".
    """
    start = ';'


class GlossElementAfterColon(GlossElement):
    """
    Rule 4C. Gloss element corresponding to "hidden" object language elements are separated by ":".
    """
    start = ':'


class GlossElementAfterBackslash(GlossElement):
    """
    Rule 4D. Morphophonological change is marked with a leading "\".
    """
    start = '\\'


class PatientlikeArgument(GlossElement):
    """
    Rule 4E. Patient-like arguments are marked with a leading ">".

    Note: Infer the agent-like argument by looking up the `prev` property.
    """
    start = '>'


class NonovertElement(GlossElement):
    """
    Rule 6. Non-overt elements can be enclosed in square brackets.
    """
    start = '['
    end = ']'


class InherentCategory(GlossElement):
    """
    Rule 7. Inherent categories can be enclosed in round brackets.
    """
    start = '('
    end = ')'


class GlossElements(list):
    """
    A container class for a list of `GlossElement` instances, together with functionality to
    round-trip from `str`.
    """
    def __str__(self):
        s, prev_enclosed = '', False
        for ge in self:
            if prev_enclosed and ge.end:
                # Another enclosed element!
                assert prev_enclosed == ge.end
                if s:
                    # Remove the prematurely appended end marker:
                    s = s[:-1]
                s += GlossElement.start
                s += ge
                s += ge.end
            else:
                if (s and not prev_enclosed) or ge.end:
                    s += ge.start
                s += str(ge)
                if ge.end:
                    s += ge.end
            prev_enclosed = ge.end
        return s

    @staticmethod
    def _iter_gloss_elements(s, type_):
        classes = {GlossElement.start: GlossElement} if type_ == 'gloss' else {}
        for cls in GlossElement.__subclasses__():
            if (not cls.in_gloss_only) or type_ == 'gloss':
                assert cls.start not in classes
                classes[cls.start] = cls
        e, cls = '', GlossElement
        s = list(reversed(s))
        while s:
            c = s.pop()
            if c in classes:
                if e:
                    # Note: We allow the complete morpheme gloss to start with a separator!
                    # That is required for infixes, but otherwise not mentioned in LGR.
                    yield cls(e)
                e, cls = '', classes[c]
                if cls.end:  # Consume the characters up to the end marker.
                    cc = s.pop()
                    while cc != cls.end:
                        e += cc
                        cc = s.pop()
                    for ee in e.split(GlossElement.start):
                        yield cls(ee)
                    e, cls = '', GlossElement
            else:
                e += c
        if e:
            yield cls(e)

    @classmethod
    def from_morpheme(cls, s, type_):
        res, prev = [], None
        for ge in GlossElements._iter_gloss_elements(s, type_):
            if prev:
                ge.prev = prev
                prev.next = ge
            res.append(ge)
            prev = ge
        return cls(res)


class Morpheme(str):
    """
    Rule 2. Morphemes are separated by "-".
    """
    sep = '-'

    def __init__(self, s):
        self.type = None
        self.prev = None
        self.next = None

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self.encode('ascii', 'replace').decode())

    @property
    def first(self):
        return not bool(self.prev)

    @property
    def last(self):
        return not bool(self.next)

    @property
    def gloss_elements(self):
        return GlossElements.from_morpheme(str(self), self.type)

    @property
    def lexical_concepts(self):
        if self.type == 'gloss':
            res = []
            s = ''
            for ge in self.gloss_elements:
                if isinstance(ge, (GlossElementAfterColon, GlossElementAfterSemicolon)):
                    # Something new is starting.
                    if s:
                        res.append(s)
                    if not ge.is_category_label:
                        s = str(ge)
                else:
                    if s:
                        s += '_'
                    s += str(ge)
            if s:
                res.append(s)
            return res


class MorphemeAfterEquals(Morpheme):
    """
    Rule 2. Clitics are separated by "=".
    """
    sep = '='


class MorphemeAfterTilde(Morpheme):
    """
    Rule 10. Reduplication is separated by "~".
    """
    sep = '~'


class MorphemeList(list):
    def __str__(self):
        s = ''
        for m in self:
            if s:
                s += m.sep
            s += str(m)
        return s

    @classmethod
    def from_string(cls, s, type_):
        assert type_ in ['word', 'gloss']
        classes = {Morpheme.sep: Morpheme}
        for c in Morpheme.__subclasses__():
            assert c.sep not in classes
            classes[c.sep] = c
        res = []
        e, c = '', Morpheme
        for t in s:
            if t in classes:
                if c:
                    res.append(c(e))
                e, c = '', classes[t]
            else:
                e += t
        if e:
            res.append(c(e))
        p = None
        for e in res:
            e.type = type_
            e.prev = p
            if p:
                p.next = e
            p = e
        return cls(res)


@attr.s
class GlossedWord(object):
    word = attr.ib()
    gloss = attr.ib()
    strict = attr.ib(default=False)
    word_morphemes = attr.ib(default=attr.Factory(list))
    gloss_morphemes = attr.ib(default=attr.Factory(list))

    def __attrs_post_init__(self):
        ww, gg = split_morphemes(self.word), split_morphemes(self.gloss)
        if self.strict and not len(ww) == len(gg):
            raise ValueError(
                'Morpheme separator mismatch: {} :: {}'.format(self.word, self.gloss))
        for w, g in zip(ww, gg):
            if w in MORPHEME_SEPARATORS and w != g:
                raise ValueError(
                    'Morpheme separator mismatch: {} :: {}'.format(self.word, self.gloss))
        self.word_morphemes = MorphemeList.from_string(self.word, 'word')
        self.gloss_morphemes = MorphemeList.from_string(self.gloss, 'gloss')

    @property
    def glossed_morphemes(self):
        return list(zip(self.word_morphemes, self.gloss_morphemes))

    @property
    def stripped_word(self):
        return ''.join(
            c for c in self.word if
            unicodedata.category(c) not in {'Po', 'Pf', 'Ps', 'Pd', 'Pe', 'Sm'})


# Now we can define the list of morpheme separators:
MORPHEME_SEPARATORS = [cls.sep for cls in [Morpheme] + Morpheme.__subclasses__()]


def split_morphemes(s):
    return re.split('({})'.format('|'.join(re.escape(c) for c in MORPHEME_SEPARATORS)), s)
