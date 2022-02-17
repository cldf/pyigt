"""
Support for parsing the notation for morpheme/gloss structure proposed by the
Leipzig Glossing Rules.
"""
import re

import attr

from pyigt.util import is_standard_abbr

__all__ = [
    # Types of morpheme gloss elements:
    'GlossElement', 'Infix', 'DistinctGlossElement', 'HiddenMorphemeGlossElement',
    'MorphophonologicalChange', 'PatientlikeArgument', 'NonovertElement', 'InherentCategory',
    # Types of morphemes:
    'Morpheme', 'Clitic', 'MorphologicallyBoundWord',
    # Wrapper
    'GlossedWord',
]


class GlossElement(str):
    # Rule 4. Separated by "."
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
        return re.fullmatch('[A-Z]+', self)


class Infix(GlossElement, str):
    # Rule 9. Enclosed in angle brackets.
    start = '<'
    end = '>'
    in_gloss_only = False


class DistinctGlossElement(GlossElement):
    # Rule 4B. Separated by ";"
    start = ';'


class HiddenMorphemeGlossElement(GlossElement):
    # Rule 4C. Separated by ":"
    start = ':'


class MorphophonologicalChange(GlossElement):
    # Rule 4D. Separated by "\"
    start = '\\'


class PatientlikeArgument(GlossElement):
    # Rule 4E, Separated by ">". Note: Must distinguish from infixes!
    start = '>'


class NonovertElement(GlossElement):
    # Rule 6. Enclosed in square brackets.
    start = '['
    end = ']'


class InherentCategory(GlossElement):
    # Rule 7. Enclosed in round brackets
    start = '('
    end = ')'


class GlossElements(list):
    def __str__(self):
        s, prev_enclosed = '', False
        for ge in self:
            if (s and not prev_enclosed) or ge.end:
                s += ge.start
            s += str(ge)
            if ge.end:
                s += ge.end
            prev_enclosed = bool(ge.end)
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
                    yield cls(e)
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
    sep = '-'

    def __new__(cls, content):
        res = str.__new__(cls, content)
        res.type = None
        return res

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self.encode('ascii', 'replace').decode())

    @property
    def gloss_elements(self):
        return GlossElements.from_morpheme(str(self), self.type)


class Clitic(Morpheme):
    # Rule 2. Separated by "="
    sep = '='


class MorphologicallyBoundWord(Morpheme):
    # Rule 2A. Separated by " -" in the object language line, by "-" in the gloss.
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
        for e in res:
            e.type = type_
        return cls(res)


@attr.s
class GlossedWord(object):
    word = attr.ib()
    gloss = attr.ib()
    word_morphemes = attr.ib(default=attr.Factory(list))
    gloss_morphemes = attr.ib(default=attr.Factory(list))

    def __attrs_post_init__(self):
        for sep in '-=~':
            # Rule 2 and 10.
            assert self.word.count(sep) == self.gloss.count(sep)
        self.word_morphemes = MorphemeList.from_string(self.word, 'word')
        self.gloss_morphemes = MorphemeList.from_string(self.gloss, 'gloss')

    @property
    def glossed_morphemes(self):
        return list(zip(self.word_morphemes, self.gloss_morphemes))
