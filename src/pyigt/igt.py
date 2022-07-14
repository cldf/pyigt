import re
import enum
import json
import types
import shutil
import typing
import pathlib
import tempfile
import itertools
import collections
import unicodedata

from tabulate import tabulate
import segments
import attr
from csvw.dsv import UnicodeWriter, reader
from csvw.metadata import Link
from pycldf import Dataset
import pycldf

try:
    import lingpy
except ImportError:  # pragma: no cover
    lingpy = False

from pyigt.util import expand_standard_abbr
from pyigt.lgrmorphemes import (
    GlossedWord, split_morphemes, remove_morpheme_separators, GlossedMorpheme
)

__all__ = ['IGT', 'Corpus', 'LGRConformance']

NON_OVERT_ELEMENT = '∅'


def with_lingpy():
    if not lingpy:
        raise ValueError('pyigt must be installed with lingpy support for this functionality! '
                         'Run `pip install pyigt[lingpy]`')
    return lingpy


@enum.unique
class LGRConformance(enum.IntEnum):
    """
    Conformance levels with respect to alignment of phrase and gloss of an `IGT`.

    We distinguish the following levels:

    - morpheme-aligned (IGT conforms to LGR Rule 2)
    - word-aligned (IGT conforms to LGR Rule 1, but not Rule 2)
    - unaligned (IGT does not conform to LGR Rule 1)
    """
    MORPHEME_ALIGNED = 2
    WORD_ALIGNED = 1
    UNALIGNED = 0


def parse_phrase(p):
    """
    We must take LGR Rule 2A into account, i.e. attach morphemes separated by " -" to the
    preceding word.
    """
    if isinstance(p, str):
        rule2a = re.compile(r'([^\s]+) -')
        return [
            w.replace('|||', ' ') for w in rule2a.sub(lambda m: m.groups()[0] + '|||-', p).split()]
    return p


@attr.s
class IGT(object):
    """
    The main trait of IGT is the alignment of words and glosses. Thus, we are mostly interested
    in the two aligned "lines": the analyzed text and the glosses, rather than trying to support
    any number of tiers, and alignment based on timestamps or similar.
    Thus, an `IGT` instance is a `list` of aligned words, and each aligned word a `list` of aligned
    morphemes. This structure can be exploited to access parts of the alignment, see
    :meth:`IGT.__getitem__`

    :ivar phrase: `list` of `str` representing the gloss-aligned words of the IGT.
    :ivar gloss: `list` of `str` representing the word-aligned glosses of the IGT.
    :ivar id: Optional identifier, can be used for referencing the `IGT` if it part of a `Corpus`.
    :ivar properties: `typing.Dict[str, object]` storing additional properties of an `IGT`, e.g. \
    additional column values read from a row in a CLDF ExampleTable.
    :ivar language: Optional language identifier, specifying the object language of the `IGT`.
    :ivar translation: Optional translation of the phrase.
    :ivar abbrs: Optional `dict` providing descriptions of gloss labels used in the `IGT`.
    :ivar strict: `bool` flag signaling whether to parse the `IGT` in strict mode, i.e. requiring \
    matching morpheme separators in phrase and gloss, or not.

    .. note::

        **LGR Conformance**

        While the main purpose of an `IGT` is providing access to its words, morphemes and glosses,
        it also supports error/conformance checking. Thus, it is possible to initialize an `IGT`
        with "broken" data.

        .. code-block:: python

            >>> from pyigt import IGT
            >>> igt = IGT(phrase='two words', gloss='ONE.GLOSS')
            >>> igt.conformance
            <LGRConformance.UNALIGNED: 0>

        So before processing `IGT` instances, it should be checked whether the conformance level
        (see :class:`LGRConformance`) of the `IGT` is sufficient for the downstream requirements.
        Otherwise, accessing properties like :meth:`IGT.glossed_words` may lead to unexpected
        results:

        .. code-block:: python

            >>> igt.glossed_words  # we extract as many glossed words as possible ...
            [<GlossedWord word=a gloss=C>]
            >>> len(igt)
            1
            >>> len(igt.phrase)
            2
            >>> igt = IGT(phrase='multi-morph', gloss='GLOSS')
            >>> igt.conformance
            <LGRConformance.WORD_ALIGNED: 1>
            >>> igt[0].glossed_morphemes  # we extract as many glossed morphemes as possible ...
            [<GlossedMorpheme morpheme=multi gloss=GLOSS>]
    """
    phrase = attr.ib(
        validator=attr.validators.instance_of(list),
        converter=parse_phrase,
    )
    gloss = attr.ib(
        validator=attr.validators.instance_of(list),
        converter=lambda g: g.split() if isinstance(g, str) else g,
    )
    id = attr.ib(default=None)
    properties = attr.ib(validator=attr.validators.instance_of(dict), default=attr.Factory(dict))
    language = attr.ib(default=None)
    translation = attr.ib(default=None)
    abbrs = attr.ib(validator=attr.validators.instance_of(dict), default=attr.Factory(dict))
    strict = attr.ib(default=False)

    def __attrs_post_init__(self):
        if self.translation:
            p = re.compile(r'\((?P<abbrs>((\s*,\s*)?[A-Z][A-Z0-9]*\s*=\s*[^,)]+)+)\)')
            abbrs = p.search(self.translation)
            if abbrs:
                for abbr in abbrs.group('abbrs').split(','):
                    abbr, _, label = abbr.partition('=')
                    self.abbrs[abbr.strip()] = label.strip()
                self.translation = p.sub('', self.translation).strip()
            if self.translation[0] == "'" or unicodedata.category(self.translation[0]) == 'Pi':
                # Punctuation, Initial quote
                self.translation = self.translation[1:].strip()
            if self.translation[-1] == "'" or \
                    unicodedata.category(self.translation[-1]) == 'Pf':
                # Punctuation, Final quote
                self.translation = self.translation[:-1].strip()

    def __len__(self):
        return len(self.glossed_words)

    def __iter__(self):
        yield from self.glossed_words

    @property
    def glossed_words(self) -> typing.List[GlossedWord]:
        return [GlossedWord(w, g, strict=self.strict) for w, g in zip(self.phrase, self.gloss)]

    @property
    def prosodic_words(self) -> typing.List[GlossedWord]:
        """
        Interpret an IGT's phrase prosodically, i.e.

        1. splits prosodically free elements marked with " -" separator and
        2. conflates clitics.

        Use :meth:`IGT.as_prosodic` to get an `IGT` instance initialised from the prosodic words
        of an `IGT` instance.
        """
        res = []
        for w, g in zip(self.phrase, self.gloss):
            word, gloss = '', ''
            morphemes = split_morphemes(w)
            morpheme_glosses = split_morphemes(g)
            for wm, gm in zip(morphemes, morpheme_glosses):
                if wm == '-' and word and word[-1] == ' ':
                    assert gm == '-'
                    res.append(GlossedWord(word.strip(), gloss, strict=self.strict))
                    word, gloss = '', ''
                else:
                    word += wm
                    gloss += gm
            if word:
                res.append(GlossedWord(word, gloss, strict=self.strict))
        return res

    @property
    def morphosyntactic_words(self) -> typing.List[GlossedWord]:
        """
        Interpret an IGT's phrase morphosyntactically, i.e.

        1. conflate prosodically free elements marked with " -" separator and
        2. split clitics into separate words.

        Use :meth:`IGT.as_morphosyntactic` to get an `IGT` instance initialised from the
        morphosyntactic words of an `IGT` instance.
        """
        res = []
        for w, g in zip(self.phrase, self.gloss):
            res.extend([
                GlossedWord(ww, gg, strict=self.strict)
                for ww, gg in zip(w.split('='), g.split('='))])
        return res

    def as_prosodic(self) -> 'IGT':
        """
        .. code-block:: python

            >>> from pyigt import IGT
            >>> igt = IGT(phrase='a=bcd -e', gloss='A=BCD-E')
            >>> len(igt) != len(igt.as_prosodic())
            True
            >>> igt[0].word
            'a=bcd -e'
            >>> igt.as_prosodic()[0].word
            'a=bcd'
        """
        return IGT(
            phrase=[gw.word for gw in self.prosodic_words],
            gloss=[gw.gloss for gw in self.prosodic_words],
            id=self.id,
            properties=self.properties,
            language=self.language,
            translation=self.translation,
            abbrs=self.abbrs,
            strict=self.strict,
        )

    def as_morphosyntactic(self):
        """
        .. code-block:: python

            >>> from pyigt import IGT
            >>> igt = IGT(phrase='a=bcd -e', gloss='A=BCD-E')
            >>> len(igt) != len(igt.as_morphosyntactic())
            True
            >>> igt[0].word
            'a=bcd -e'
            >>> igt.as_morphosyntactic()[-1].word
            'bcd -e'
        """
        return IGT(
            phrase=[gw.word for gw in self.morphosyntactic_words],
            gloss=[gw.gloss for gw in self.morphosyntactic_words],
            id=self.id,
            properties=self.properties,
            language=self.language,
            translation=self.translation,
            abbrs=self.abbrs,
            strict=self.strict,
        )

    @property
    def gloss_abbrs(self) -> collections.OrderedDict:
        res = collections.OrderedDict()
        for gw in self.glossed_words:
            for gm in gw:
                for element in gm.gloss.elements:
                    # We disregard "I".
                    if element != 'I' and element.is_category_label:
                        if element in self.abbrs:
                            res[element] = self.abbrs[element]
                        else:
                            desc = expand_standard_abbr(element)
                            res[element] = desc if desc != element else None
        return res

    def __str__(self):
        """
        A plain text representation of the IGT, to be viewed with a monospaced font to make
        alignments work.
        """
        return '{0}\n{1}{2}'.format(
            self.primary_text,
            tabulate([self.gloss], self.phrase, tablefmt='plain'),
            '\n‘{}’'.format(self.translation) if self.translation else '',
        )

    def pprint(self):
        abbrs = [(k, v) for k, v in self.gloss_abbrs.items() if v]
        if abbrs:
            mlen = max(len(a[0]) for a in abbrs)
            abbrs = ''.join('\n  {} = {}'.format(k.ljust(mlen), v) for k, v in abbrs)
        print('{}{}'.format(self, abbrs or ''))

    def __getitem__(self, i: typing.Union[int, typing.Tuple[int, typing.Union[int, slice]]]) \
            -> typing.Union[typing.List, GlossedWord, GlossedMorpheme]:
        """
        Provide access to `GlossedWord` or `GlossedMorpheme` (s) by zero-based index.

        :param i: An `int` index to reference a `GlossedWord` or a (`int`, `int`) tuple,\
        referencing a `GlossedMorpheme`.

        .. code-block:: python

            >>> from pyigt import IGT
            >>> igt = IGT(phrase="zəp-le: ȵi-ke: pe-ji qeʴlotʂu-ʁɑ,", gloss="a-DEF b-IN c-CSM d-LO")
            >>> igt[0].word
            'zəp-le:'
            >>> [gw.word for gw in igt[2:]]
            ['pe-ji', 'qeʴlotʂu-ʁɑ,']
            >>> str(igt[0, 0].morpheme)
            'zəp'
            >>> [str(gm.morpheme) for gm in igt[1, 0:]]  # All morphemes of the second word
            ['ȵi', 'ke:']
            >>> [str(gm.morpheme) for gm in igt[0:, 0]]  # First morpheme in each word
            ['zəp', 'ȵi', 'pe', 'qeʴlotʂu']
        """
        if isinstance(i, tuple):
            assert len(i) == 2
            word = self.glossed_words[i[0]]
            if isinstance(word, list):
                return [w[i[1]] for w in word]
            return word[i[1]]
        return self.glossed_words[i]

    @property
    def conformance(self) -> LGRConformance:
        """
        Alignment level of the `IGT`.
        """
        if self.is_valid(strict=True):
            return LGRConformance.MORPHEME_ALIGNED
        if self.is_valid():
            return LGRConformance.WORD_ALIGNED
        return LGRConformance.UNALIGNED

    def is_valid(self, strict: bool = False) -> bool:
        try:
            self.check(strict=strict)
            return True
        except (ValueError, AssertionError):
            return False

    def check(self, strict: bool = False, verbose: bool = False):
        """
        :param strict: If `True`, also check Rule 2: Morpheme-by-morpheme correspondence.
        """
        res = len(self.phrase) == len(self.gloss)
        if not res:
            if verbose:
                print('\t'.join(self.phrase))
                print('\t'.join(self.gloss))
            raise ValueError(
                'Rule 1 violated: Number of words does not match number of word glosses!')
        if strict:
            for i, (m, g) in enumerate(zip(self.phrase, self.gloss)):
                try:
                    GlossedWord(m, g, strict=True)
                except ValueError:
                    if verbose:
                        print(self.phrase[i])
                        print(self.gloss[i])
                    raise ValueError(
                        'Rule 2 violated: Number of morphemes does not match number of morpheme '
                        'glosses!')

    @property
    def phrase_text(self) -> str:
        return ' '.join([w or '' for w in self.phrase])

    @property
    def primary_text(self) -> str:
        """
        The primary text of the `IGT`, i.e. the phrase stripped off morpheme separators.
        """
        try:
            words = []
            for gw in self.glossed_words:
                words.append(''.join(gm.morpheme for gm in gw if gm.morpheme != NON_OVERT_ELEMENT))
            return ' '.join(words)
        except AssertionError:
            return remove_morpheme_separators(self.phrase_text)

    @property
    def gloss_text(self) -> str:
        return ' '.join(self.gloss)


def _clean_lexical_concept(s):
    s = re.sub(r'†\(([^)]+)\)', lambda m: m.groups()[0], s)
    return s.replace('†', '').strip()


class Corpus(object):
    """
    A Corpus is an immutable, ordered list of `IGT` instances.

    It provides access to concordance-like aggregated statistics of its texts.

    :ivar monolingual: Flag signaling whether the corpus is monolingual or contains `IGT` from \
    different object languages.
    """
    def __init__(self, igts: typing.Iterable[IGT], fname=None, clean_lexical_concept=None):
        self.clean_lexical_concept = clean_lexical_concept or _clean_lexical_concept
        self.fname = fname
        self._igts = collections.OrderedDict([(igt.id or n, igt) for n, igt in enumerate(igts)])
        self._concordance = dict(
            grammar=collections.defaultdict(list),
            lexicon=collections.defaultdict(list),
            form=collections.defaultdict(list),
        )
        # Since changing the IGTs in the corpus is not allowed, we can compute concordances right
        # away.
        for idx, igt in self._igts.items():
            if not igt.is_valid(strict=True):  # We ignore non-morpheme-aligned IGTs.
                continue
            for i, gw in enumerate(igt):
                for j, gm in enumerate(gw):
                    if not gm.form:
                        continue

                    ref = (idx, i, j)
                    for g in gm.grammatical_concepts:
                        self._concordance['grammar'][g].append(ref)
                    self._concordance['lexicon'][' // '.join(gm.lexical_concepts)].append(ref)
                    self._concordance['form'][gm.form].append(ref)
        self.monolingual = len(set(igt.language for igt in self._igts.values())) == 1

    @property
    def grammar(self) -> typing.Dict[str, typing.List[typing.Tuple[int, int, int]]]:
        """
        Maps grammatical concepts to lists of occurrences.

        .. code-block:: python

            >>> from pyigt import Corpus, IGT
            >>> igt = IGT(phrase="ni-c-chihui-lia in no-piltzin ce calli",
            ...           gloss="1SG.SUBJ-3SG.OBJ-mach-APPL DET 1SG.POSS-Sohn ein Haus")
            >>> c = Corpus([igt])
            >>> [[c[ref] for ref in c.grammar[k]] for k in c.grammar if k.startswith('1SG')]
            [[<GlossedMorpheme morpheme=ni gloss=1SG.SUBJ>],
             [<GlossedMorpheme morpheme=no gloss=1SG.POSS>]]
        """
        return self._concordance['grammar']

    @property
    def lexicon(self) -> typing.Dict[str, typing.List[typing.Tuple[int, int, int]]]:
        """
        Maps lexical concepts to lists of occurrences.

        .. code-block:: python

            >>> from pyigt import Corpus, IGT
            >>> igt = IGT(phrase="ni-c-chihui-lia in no-piltzin ce calli",
            ...           gloss="1SG.SUBJ-3SG.OBJ-mach-APPL DET 1SG.POSS-Sohn ein Haus")
            >>> c = Corpus([igt])
            >>> [c[ref] for ref in c.lexicon['Sohn']]
            [<GlossedMorpheme morpheme=piltzin gloss=Sohn>]
        """
        return self._concordance['lexicon']

    @property
    def form(self) -> typing.Dict[str, typing.List[typing.Tuple[int, int, int]]]:
        """
        Maps grammatical concepts to lists of occurrences.

        .. code-block:: python

            >>> from pyigt import Corpus, IGT
            >>> igt = IGT(phrase="ni-c-chihui-lia in no-piltzin ce calli",
            ...           gloss="1SG.SUBJ-3SG.OBJ-mach-APPL DET 1SG.POSS-Sohn ein Haus")
            >>> c = Corpus([igt])
            >>> [k for k in c.form]
            ['ni', 'c', 'chihui', 'lia', 'in', 'no', 'piltzin', 'ce', 'calli']
        """
        return self._concordance['form']

    @staticmethod
    def get_column_names(cldf: Dataset) -> types.SimpleNamespace:
        # We lookup local column names by ontology term:
        lookup = [
            ('id', 'id'),
            ('phrase', 'analyzedWord'),
            ('gloss', 'gloss'),
            ('translation', 'translatedText'),
            ('language', 'languageReference'),
        ]
        return types.SimpleNamespace(**{
            k: cldf['ExampleTable', v].name if ('ExampleTable', v) in cldf else None
            for k, v in lookup})

    @classmethod
    def from_cldf(cls, cldf: Dataset) -> 'Corpus':
        """
        Instantiate a corpus of IGT examples from a CLDF dataset.

        :param cldf: a `pycldf.Dataset` instance.
        :param spec: a `CorpusSpec` instance, specifying how to interpret markup in the corpus.
        """
        cols = cls.get_column_names(cldf)
        igts = [
            IGT(
                id=igt[cols.id],
                gloss=igt[cols.gloss],
                phrase=igt[cols.phrase],
                language=igt.get(cols.language),
                translation=igt.get(cols.translation),
                properties=igt,
            )
            for igt in cldf['ExampleTable']]
        return cls(
            igts,
            fname=cldf.tablegroup._fname.parent / str(cldf['ExampleTable'].url))

    @classmethod
    def from_stream(cls, stream) -> 'Corpus':
        from csvw.metadata import TableGroup
        cldf = Dataset(TableGroup(fname=pathlib.Path('tmp.json')))
        cldf.add_component('ExampleTable')

        cols = cls.get_column_names(cldf)
        igts = [
            IGT(
                id=igt[cols.id],
                gloss=igt[cols.gloss].split('\\t'),
                phrase=igt[cols.phrase].split('\\t'),
                language=igt.get(cols.language),
                properties=igt,
            )
            for igt in reader(stream.read().splitlines(), dicts=True)]
        return cls(igts)

    @classmethod
    def from_path(cls, path: typing.Union[str, pathlib.Path]) -> 'Corpus':
        """
        Instantiate a corpus from a file path.

        :param path: Either a path to a CLDF dataset's metadata file or to a CLDF Examples \
        component as CSV file. Note that in the latter case, the file must use the default \
        column names, as defined in the CLDF ontology.
        """
        if isinstance(path, str):
            path = pathlib.Path(path)
        if path.suffix == '.json':
            return cls.from_cldf(Dataset.from_metadata(path))
        # We are given only an ExampleTable. Let's create the appropriate dataset:
        header = None
        for d in reader(path, dicts=True):
            header = list(d.keys())
            break
        ds = Dataset.from_metadata(
            pathlib.Path(pycldf.__file__).parent / 'modules' / 'Generic-metadata.json')
        ds.tablegroup._fname = path.parent / 'cldf-metadata.json'
        t = ds.add_component('ExampleTable')
        t.url = Link(path.name)
        default_cols = [col.name for col in t.tableSchema.columns]
        ds.remove_columns(t, *list(set(default_cols) - set(header)))
        ds.add_columns(t, *list(set(header) - set(default_cols)))
        return cls.from_cldf(ds)

    def __len__(self):
        return len(self._igts)

    def __iter__(self):
        return iter(self._igts.values())

    def __getitem__(self, item):
        if not isinstance(item, tuple):
            return self._igts[item] if item in self._igts else list(self._igts.values())[item]
        if len(item) == 2:
            return self._igts[item[0]][item[1]]
        return self[item[0]][tuple(item[1:])]

    def get_stats(self):
        return (
            len(self),
            sum(len(igt) for igt in self),
            sum(sum(len(w) for w in igt) for igt in self))

    def get_lgr_conformance_stats(self):
        return collections.Counter([igt.conformance for igt in self])

    def write_concordance(self, ctype: str, filename=None):
        """
        :param ctype: `lexicon` or `grammar` or `form`.
        """
        conc = collections.defaultdict(list)
        for c, refs in getattr(self, ctype).items():
            for ref in refs:
                # We want one row per unique (form, language, concept, gloss).
                if ctype == 'form':
                    gloss = str(self[ref].gloss)
                    conc[c, gloss, gloss, self[ref[0]].language].append(ref)
                else:
                    conc[
                        self[ref].form,
                        self.clean_lexical_concept(c),
                        c,
                        self[ref[0]].language].append(ref)

        with UnicodeWriter(filename, delimiter='\t') as w:
            h = ['ID', 'FORM', 'GLOSS', 'GLOSS_IN_SOURCE', 'OCCURRENCE', 'REF']
            if not self.monolingual:
                h.insert(1, 'LANGUAGE_ID')
            w.writerow(h)
            # We order the rows by descending frequency:
            for i, (k, refs) in enumerate(
                    sorted(conc.items(), key=lambda x: (-len(x[1]), x[0])), start=1):
                c = [
                    i,
                    k[0],
                    k[1],
                    k[2],
                    len(refs),
                    ' '.join(['{}:{}:{}'.format(*ref) for ref in refs])]
                if not self.monolingual:
                    c.insert(1, k[3])
                w.writerow(c)

        if not filename:
            print(w.read().decode('utf8'))

    def write_concepts(self, ctype, filename=None):
        """
        :param ctype: `lexicon` or `grammar`.
        """
        def form(ref):
            return self[ref].form if self.monolingual else '{}: {}'.format(
                self[ref[0]].language, self[ref].form)

        conc = []
        for c, refs in getattr(self, ctype).items():
            if c:
                igt = self[refs[0][0]]
                conc.append([
                    self.clean_lexical_concept(c),
                    len(refs),
                    ' // '.join(sorted(set(str(self[ref].gloss) for ref in refs))),
                    ' // '.join(sorted(set(form(ref) for ref in refs))),
                    igt.phrase_text,
                    igt.gloss_text,
                ])

        with UnicodeWriter(filename, delimiter='\t') as w:
            w.writerow(
                ['ID', 'ENGLISH', 'OCCURRENCE', 'CONCEPT_IN_SOURCE', 'FORMS', 'PHRASE', 'GLOSS'])
            for i, row in enumerate(sorted(conc, key=lambda x: -x[1]), start=1):
                w.writerow([i] + row)
        if not filename:
            print(w.read().decode('utf8'))

    def check_glosses(self, level=2):
        count = 1
        for idx, igt in self._igts.items():
            if not igt.is_valid() and level >= 1:
                print('[{0} : first level {1}]'.format(idx, count))
                print(igt.phrase)
                print(igt.gloss)
                print('---')
                count += 1
            if level >= 2:
                for i, (w, m) in enumerate(zip(igt.phrase, igt.gloss), start=1):
                    try:
                        GlossedWord(w, m, strict=True)
                    except ValueError:
                        print('[{0}:{1} : second level {2}]'.format(idx, i, count))
                        print(w)
                        print(m)
                        print('---')
                        count += 1

    def get_wordlist(
            self,
            doculect='base',
            profile=False,
            ref='crossid',
            lexstat=True,
            threshold=0.4):
        """
        Return a classical wordlist from the data.
        """
        if profile:
            profile = segments.Tokenizer(profile)
            tokenize = lambda x: profile('^' + x + '$', column='IPA').split()  # noqa: E731
        else:
            tokenize = with_lingpy().ipa2tokens

        D = {
            0: [
                'doculect',
                'concept',
                'concept_in_source',
                'concept_type',
                'form',
                'tokens',
                'occurrences',
                'word_forms',
                'gloss_forms',
                'phrase_example',
                'gloss_example',
                'references',
            ]
        }
        idx = 1
        # Iterate over unique (cleaned concept, form, language, gloss) tuples.
        i = 0
        for form, refs in self.form.items():
            for (lid, gloss), morphrefs in itertools.groupby(
                sorted(refs, key=lambda r: (self[r[0]].language, str(self[r].gloss))),
                lambda r: (self[r[0]].language, str(self[r].gloss))
            ):
                morphrefs = list(morphrefs)
                gm = self[morphrefs[0]]
                gw = self[morphrefs[0][:2]]
                igt = self[morphrefs[0][0]]
                i += 1
                concepts = \
                    list(itertools.zip_longest(gm.lexical_concepts, [], fillvalue='lexicon')) + \
                    list(itertools.zip_longest(gm.grammatical_concepts, [], fillvalue='grammar'))
                for concept, ctype in concepts:
                    concept = self.clean_lexical_concept(concept)
                    tokens = tokenize(form)
                    # check tokens
                    try:
                        with_lingpy().tokens2class(tokens, 'sca')
                        check = True
                    except:  # noqa: E722, # pragma: no cover
                        check = False
                    if concept.strip() and check:
                        D[idx] = [
                            doculect if self.monolingual else lid,
                            concept,
                            gloss,
                            ctype,
                            form,
                            tokens,
                            len(morphrefs),
                            ' '.join(m.form for m in gw),
                            ' '.join(m.gloss for m in gw),
                            igt.phrase_text,
                            igt.gloss_text,
                            ' '.join('{}:{}:{}'.format(*ref) for ref in morphrefs)]
                        idx += 1
                    else:
                        print('[!] Problem with "{0}" / [{1}] [{2}] / {3} {4} {5}'.format(
                            concept, form, tokens, *morphrefs[0]))
        wl = with_lingpy().Wordlist(D)

        if lexstat:
            wl = with_lingpy().LexStat(D)
            wl.cluster(method='sca', threshold=threshold, ref=ref)
        else:
            wl.add_entries('cog', 'concept,form', lambda x, y: x[y[0]] + '-' + x[y[1]])
            wl.renumber('cog', ref)
        return wl

    def get_profile(self, clts=None, filename=None) -> segments.Profile:
        """
        Compute an orthography profile with LingPy's function.

        :param filename: Write the computed profile to a file in addition to returning it.
        :return: `segments.Profile` instance.
        """
        clts = clts.bipa if clts else None

        D = {0: ['doculect', 'concept', 'ipa']}
        for i, key in enumerate(self.form, start=1):
            D[i] = ['dummy', str(self[self.form[key][0]].gloss), key]
        wordlist = with_lingpy().basic.wordlist.Wordlist(D)

        if not filename:
            with tempfile.NamedTemporaryFile(delete=FileExistsError) as fp:
                pass
            p = pathlib.Path(fp.name)
        else:
            p = pathlib.Path(filename)

        with UnicodeWriter(p, delimiter='\t') as w:
            w.writerow(['Grapheme', 'IPA', 'Example', 'Count', 'Unicode'])
            for line in with_lingpy().sequence.profile.context_profile(
                    wordlist, ref='ipa', clts=clts):
                w.writerow([line[0], line[1], line[2], line[4], line[5]])

        res = segments.Profile.from_file(p)
        if not filename:
            p.unlink()
        return res

    def write_app(self, dest='app'):
        # idxs must be in index 2 of wordlist, form 0, and concept 1
        # concordance 0 is phrase, 1 is gloss

        wordlist = self.get_wordlist()
        WL, CN = collections.OrderedDict(), collections.OrderedDict()
        for idx, form, concept, refs in wordlist.iter_rows('form', 'concept', 'references'):
            WL[idx] = [
                form,
                concept,
                [[int(y) for y in x.split(':')] for x in refs.split()],
                wordlist[idx, 'tokens'],
            ]

            for line in WL[idx][2]:
                igt = self[str(line[0])]
                CN[line[0]] = [
                    igt.phrase,
                    igt.gloss,
                ]
                # FIXME: must add additional IGT data from ExampleTable row!
        dest = pathlib.Path(dest)
        assert dest.is_dir()
        with dest.joinpath('script.js').open('w', encoding='utf8') as f:
            f.write('var WORDLIST = ' + json.dumps(WL, indent=2) + ';\n')
            f.write('var CONC = ' + json.dumps(CN, indent=2) + ';\n')
        index = dest / 'index.html'
        if not index.exists():
            shutil.copy(str(pathlib.Path(__file__).parent.joinpath('index.html')), str(index))
