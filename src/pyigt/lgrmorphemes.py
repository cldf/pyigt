"""
`pyigt` supports the notation for morpheme/gloss structure proposed by the
`Leipzig Glossing Rules <https://www.eva.mpg.de/lingua/resources/glossing-rules.php>`_.

According to LGR Rule 1, object language and gloss lines have to be word-aligned. Such aligned
pairs of a word and a corresponding gloss are modeled via the :class:`GlossedWord` class.

If an IGT conforms to Rule 2, glossed words are lists of aligned
:class:`~pyigt.lgrmorphemes.GlossedMorpheme` pairs.

The provisions of Rule 4 (and following), i.e. the structure of morpheme glosses, is implemented
as subclasses of :class:`GlossElement`.
"""
import re
import itertools
import typing
import unicodedata

import attr

from pyigt.util import is_standard_abbr, GENERIC_ABBR_PATTERN

__all__ = [
    # Types of morpheme gloss elements:
    'GlossElement', 'Infix', 'GlossElementAfterSemicolon', 'GlossElementAfterColon',
    'GlossElementAfterBackslash', 'PatientlikeArgument', 'NonovertElement', 'InherentCategory',
    # Types of morphemes:
    'Morpheme', 'MORPHEME_SEPARATORS', 'split_morphemes', 'remove_morpheme_separators',
    # Wrapper
    'GlossedWord', 'GlossedMorpheme',
]
MORPHEME_SEPARATORS = [
    '-',  # Rule 2
    '=',  # Rule 2, clitics
    '~',  # Rule 10
]


def split_morphemes(s):
    return re.split('({})'.format('|'.join(re.escape(c) for c in MORPHEME_SEPARATORS)), s or '')


def remove_morpheme_separators(s):
    return ''.join(ss for ss in split_morphemes(s) if ss not in MORPHEME_SEPARATORS)


class GlossElement(str):
    """
    Rule 4. Gloss elements are separated by ".".

    :ivar start: Specifies the separator to use when combining a `GlossElement` with another.
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
        return GENERIC_ABBR_PATTERN.fullmatch(self)


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
    Rule 4D. Morphophonological change is marked with a leading "\\".
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
                if s and cls.end:  # Consume the characters up to the end marker.
                    cc = s.pop()
                    while s and (cc != cls.end):
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

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self.encode('ascii', 'replace').decode())

    @property
    def elements(self):
        return GlossElements.from_morpheme(str(self), self.type)


@attr.s(repr=False)
class GlossedMorpheme(object):
    """
    A (morpheme, gloss) pair.

    :ivar morpheme: The morpheme form.
    :ivar gloss: The literal gloss.
    :ivar sep: The morpheme separator preceding this morpheme.
    :ivar prev: Points to the previous `GlossedMorpheme` in a word, or `None`.
    :ivar next: Points to the next `GlossedMorpheme` in a word, or `None`.
    """
    morpheme = attr.ib()
    gloss = attr.ib()
    sep = attr.ib()
    prev = attr.ib(default=None, eq=False)
    next = attr.ib(default=None, eq=False)

    def __attrs_post_init__(self):
        self.morpheme = Morpheme(self.morpheme)
        self.morpheme.type = 'word'
        self.gloss = Morpheme(self.gloss)
        self.gloss.type = 'gloss'

    def __repr__(self):
        return '<{} morpheme={} gloss={}>'.format(
            self.__class__.__name__, self.morpheme, self.gloss)

    @property
    def first(self):
        return not bool(self.prev)

    @property
    def last(self):
        return not bool(self.next)

    @property
    def grammatical_concepts(self) -> typing.List[str]:
        """
        Grammatical concepts, referenced with category labels according to Rule 3, used in morpheme
        gloss.

        .. note::

            Gloss element separators according to Rule 4B and 4C are interpreted as signaling a
            separate concept.

        .. code-block:: python

            >>> from pyigt.lgrmorphemes import GlossedMorpheme
            >>> gm = GlossedMorpheme(morpheme='abc', gloss='ABC.DEF:GHI;JKL', sep='.')
            >>> gm.grammatical_concepts
            ['ABC.DEF', 'GHI', 'JKL']
        """
        return list(self._glosses('grammatical'))

    @property
    def lexical_concepts(self) -> typing.List[str]:
        """
        Gloss elements not recognized as category labels are interpreted as lexical concepts.

       .. code-block:: python

            >>> from pyigt.lgrmorphemes import GlossedMorpheme
            >>> gm = GlossedMorpheme(morpheme='çık', gloss='come_out', sep='.')
            >>> gm.lexical_concepts
            ['come out']
        """
        return list(self._glosses('lexical'))

    def _glosses(self, type_):
        s = ''
        for ge in self.gloss.elements:
            if isinstance(ge, (GlossElementAfterColon, GlossElementAfterSemicolon)):
                # Something new is starting.
                if s:
                    yield s.replace('_', ' ')
                if (type_ == 'lexical' and not ge.is_category_label) or \
                        (type_ == 'grammatical' and ge.is_category_label):
                    s = str(ge)
            else:
                if (type_ == 'lexical' and not ge.is_category_label) or \
                        (type_ == 'grammatical' and ge.is_category_label):
                    if s:
                        s += ge.start if ge.is_category_label else ' '
                    s += str(ge)
        if s:
            yield s.replace('_', ' ')


@attr.s(repr=False)
class GlossedWord(object):
    """
    A (word, gloss) pair, corresponding to two aligned items from IGT according to LGR.

    Provides list-like access to its :class:`GlossedMorpheme` s.
    """
    word = attr.ib()
    gloss = attr.ib()
    glossed_morphemes = attr.ib(default=attr.Factory(list), eq=False)
    strict = attr.ib(default=False, eq=False)
    is_valid = attr.ib(default=True, eq=False)

    def __attrs_post_init__(self):
        mm, gg = split_morphemes(self.word), split_morphemes(self.gloss)
        if len(mm) != len(gg):
            if self.strict:
                raise ValueError(
                    'Morpheme separator mismatch: {} :: {}'.format(self.word, self.gloss))
            else:
                self.is_valid = False
        sep, prev = None, None
        for m, g in zip(mm, gg):
            if m in MORPHEME_SEPARATORS:
                if m != g:
                    if self.strict:
                        raise ValueError(
                            'Morpheme separator mismatch: {} :: {}'.format(self.word, self.gloss))
                    else:
                        self.is_valid = False
                        break
                sep = m
            else:
                assert m and g
                gm = GlossedMorpheme(m, g, sep=sep)
                self.glossed_morphemes.append(gm)
                if prev:
                    prev.next = gm
                    gm.prev = prev
                prev = gm

    def __repr__(self):
        return '<{} word={} gloss={}>'.format(self.__class__.__name__, self.word, self.gloss)

    def __iter__(self):
        return iter(self.glossed_morphemes)

    def __getitem__(self, item):
        return self.glossed_morphemes[item]

    def __len__(self):
        return len(self.glossed_morphemes)

    @property
    def stripped_word(self) -> str:
        """
        Removes sentence-level markup and morpheme separators from `.word`.

        .. code-block:: python

            >>> from pyigt.lgrmorphemes import GlossedWord
            >>> gw = GlossedWord(word='"An-fangs', gloss="a-b")
            >>> gw.stripped_word
            'Anfangs'
        """
        return ''.join(
            c for c in self.word if
            unicodedata.category(c) not in {'Po', 'Pf', 'Ps', 'Pd', 'Pe', 'Sm'})

    @property
    def word_from_morphemes(self):
        return ''.join(itertools.chain(
            *[(gm.sep if gm.prev else '', str(gm.morpheme.elements)) for gm in self]))

    @property
    def gloss_from_morphemes(self):
        return ''.join(itertools.chain(
            *[(gm.sep if gm.prev else '', str(gm.gloss.elements)) for gm in self]))
