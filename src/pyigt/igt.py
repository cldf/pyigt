import re
import json
import shutil
import pathlib
import argparse
import tempfile
import collections

from tabulate import tabulate
import lingpy
import segments
import attr
from clldutils.misc import nfilter
from clldutils.lgr import ABBRS
from csvw.dsv import UnicodeWriter, reader
from csvw.metadata import Link
from pycldf import Dataset
import pycldf

__all__ = ['IGT', 'Corpus', 'CorpusSpec']


def iter_morphemes(s):
    """
    Split word into morphemes following the Leipzig Glossing Rules:
    - `-` and `=` (for clitics) separate morphemes, see LGR rule 2.
    - `<` and `>` enclose infixes, see LGR rule 9.
    - `~` splits reduplicated morphemes, see LGR rule 10.
    """
    morpheme, in_infix = [], False

    for c in s:
        if c in {'-', '=', '~', '<', '>'}:
            if in_infix and c != '>':
                raise ValueError('Invalid morpheme nesting: "{}"'.format(s))
            yield ''.join(morpheme)
            morpheme = []
            if c == '<':
                in_infix = True
            elif c == '>':
                in_infix = False
        else:
            morpheme.append(c)

    yield ''.join(morpheme)


@attr.s
class CorpusSpec(object):
    punctuation = attr.ib(
        validator=attr.validators.instance_of(list),
        default=list(',;.”“"()'))
    concept_replace = attr.ib(
        validator=attr.validators.instance_of(dict),
        default={'.': ' ', '†(': '', '†': ''})
    paradigm_marker = attr.ib(
        validator=attr.validators.instance_of(str),
        default=':')
    # A "simple" `CorpusSpec`, only recognizing one single-character morpheme separator, can be
    # constructed by setting `morpheme_separator`.
    morpheme_separator = attr.ib(
        validator=attr.validators.optional(attr.validators.instance_of(str)),
        default=None)
    label_pattern = attr.ib(default=re.compile('^([A-Z]+|([1-3](DL|PL|SG)))$'))

    def split_morphemes(self, s):
        if self.morpheme_separator:
            return s.split(self.morpheme_separator)
        return list(iter_morphemes(s))

    def strip_punctuation(self, s):
        for p in self.punctuation:
            s = s.replace(p, '')
        return s

    def is_grammatical_gloss_label(self, s):
        return bool((s in ABBRS) or self.label_pattern.match(s))

    def clean_concept(self, c):
        for k, v in self.concept_replace.items():
            c = c.replace(k, v)
        return c.strip()

    def _glosses(self, concept, ctype):
        return [
            g for g in nfilter(self.clean_concept(cn) for cn in concept.split(self.paradigm_marker))
            if (ctype == 'grammar' and self.is_grammatical_gloss_label(g))
            or (ctype == 'lexicon' and not self.is_grammatical_gloss_label(g))]  # noqa: W503

    def lexical_gloss(self, concept):
        return ' // '.join(self._glosses(concept, 'lexicon'))

    def grammatical_glosses(self, concept):
        return self._glosses(concept, 'grammar')


@attr.s
class IGT(object):
    """
    Interlinear Glossed Text

    The main trait of IGT is the alignment of words and glosses. Thus, we are mostly interested
    in the two aligned "lines": the analyzed text and the glosses, rather than trying to support
    any number of tiers, and alignment based on timestamps or similar.
    """
    id = attr.ib()
    phrase = attr.ib(validator=attr.validators.instance_of(list))
    gloss = attr.ib(validator=attr.validators.instance_of(list))
    properties = attr.ib(validator=attr.validators.instance_of(dict))
    spec = attr.ib(default=CorpusSpec())

    def __attrs_post_init__(self):
        self.phrase_segmented = [nfilter(self.spec.split_morphemes(m)) for m in self.phrase]
        self.gloss_segmented = [nfilter(self.spec.split_morphemes(m)) for m in self.gloss]

    @property
    def glossed_words(self):
        return list(zip(self.phrase, self.gloss))

    @property
    def glossed_morphemes(self):
        return [list(zip(p, g)) for p, g in zip(self.phrase_segmented, self.gloss_segmented)]

    def __str__(self):
        return '{0}\n{1}'.format(
            self.primary_text, tabulate([self.gloss], self.phrase, tablefmt='plain'))

    def __getitem__(self, item):
        """
        Provide access to individual (word, gloss) or (morpheme, gloss) pairs.

        :param item: An `int` index to reference a (word, gloss) pair or a (`int`, `int`) tuple,\
        referencing a (morpheme, gloss) pair.
        :return: (word, gloss) or (morpheme, gloss) pair
        """
        if not isinstance(item, tuple):
            return self.glossed_words[item]
        return self.glossed_morphemes[item[0]][item[1]]

    def is_valid(self):
        return len(self.phrase) == len(self.gloss)

    @property
    def phrase_text(self):
        return ' '.join(self.phrase)

    @property
    def primary_text(self):
        return ' '.join(''.join(self.spec.split_morphemes(w)) for w in self.phrase)

    @property
    def gloss_text(self):
        return ' '.join(self.gloss)


class Concordances(argparse.Namespace):
    def __getitem__(self, item):
        return vars(self)[item]


class Corpus(object):
    """
    A Corpus is an immutable, ordered list of `IGT` instances.
    """
    def __init__(self, igts, spec=None, fname=None):
        self.fname = fname
        self.spec = spec or CorpusSpec()
        self._igts = collections.OrderedDict([(igt.id, igt) for igt in igts])
        self._concordances = Concordances(
            grammar=collections.defaultdict(list),
            lexicon=collections.defaultdict(list),
            form=collections.defaultdict(list),
        )
        # Since changing the IGTs in the corpus is not allowed, we can compute concordances right
        # away.
        for idx, igt in self._igts.items():
            if not igt.is_valid():
                continue
            for i, (w, m) in enumerate(zip(igt.phrase_segmented, igt.gloss_segmented)):
                if len(w) != len(m):
                    continue
                for j, (morpheme, concept) in enumerate(zip(w, m)):
                    morpheme = self.spec.strip_punctuation(morpheme)
                    if not morpheme:
                        continue
                    ref = (idx, i, j)
                    for g in self.spec.grammatical_glosses(concept):
                        self._concordances.grammar[morpheme, g, concept].append(ref)
                    self._concordances.lexicon[
                        morpheme, self.spec.lexical_gloss(concept), concept].append(ref)
                    self._concordances.form[morpheme, concept, concept].append(ref)

    @classmethod
    def from_cldf(cls, cldf, spec=None):
        """
        A corpus of IGT examples provided with a CLDF dataset.

        :param cldf: a `pycldf.Dataset` instance.
        :param spec: a `CorpusSpec` instance, specifying how to interpret markup in the corpus.
        """
        spec = spec or CorpusSpec()
        _id = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#id'].name
        _phrase = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#analyzedWord'].name
        _gloss = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#gloss'].name
        igts = [
            IGT(
                id=igt[_id],
                gloss=igt[_gloss],
                phrase=igt[_phrase],
                properties=igt,
                spec=spec,
            )
            for igt in cldf['ExampleTable']]
        return cls(
            igts,
            spec=spec,
            fname=cldf.tablegroup._fname.parent / str(cldf['ExampleTable'].url))

    @classmethod
    def from_stream(cls, stream, spec=None):
        from csvw.metadata import TableGroup
        cldf = Dataset(TableGroup(fname=pathlib.Path('tmp.json')))
        cldf.add_component('ExampleTable')

        spec = spec or CorpusSpec()
        _id = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#id'].name
        _phrase = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#analyzedWord'].name
        _gloss = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#gloss'].name

        igts = [
            IGT(
                id=igt[_id],
                gloss=igt[_gloss].split('\\t'),
                phrase=igt[_phrase].split('\\t'),
                properties=igt,
                spec=spec,
            )
            for igt in reader(stream.read().splitlines(), dicts=True)]
        return cls(igts, spec=spec)

    @classmethod
    def from_path(cls, path, spec=None):
        """
        Instantiate a corpus from a file path.

        :param path: Either a path to a CLDF dataset's metadata file or to a CLDF Examples \
        component as CSV file. Note that in the latter case, the file must use the default \
        column names, as defined in the CLDF ontology.
        :return: `Corpus` instance.
        """
        if isinstance(path, str):
            path = pathlib.Path(path)
        if path.suffix == '.json':
            return cls.from_cldf(Dataset.from_metadata(path), spec=spec)
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
        return cls.from_cldf(ds, spec=spec)

    def __len__(self):
        return len(self._igts)

    def __iter__(self):
        return iter(self._igts.values())

    def __getitem__(self, item):
        if not isinstance(item, tuple):
            return self._igts[item]
        if len(item) == 2:
            return self._igts[item[0]][item[1]]
        return self._igts[item[0]][tuple(item[1:])]

    def get_stats(self):
        wordc, morpc = 0, 0
        for igt in self:
            for word in igt.phrase_segmented:
                wordc += 1
                morpc += len(word)
        return len(self._igts), wordc, morpc

    def write_concordance(self, ctype, filename=None):
        with UnicodeWriter(filename, delimiter='\t') as w:
            w.writerow(['ID', 'FORM', 'GLOSS', 'GLOSS_IN_SOURCE', 'OCCURRENCE', 'REF'])
            for i, (k, v) in enumerate(sorted(
                    self._concordances[ctype].items(), key=lambda x: (-len(x[1]), x[0])), start=1):
                w.writerow([
                    i,
                    k[0],
                    k[1],
                    k[2],
                    len(v),
                    ' '.join(['{0}:{1}:{2}'.format(x, y, z) for x, y, z in v])])
        if not filename:
            print(w.read().decode('utf8'))

    def get_concepts(self, ctype='lexicon'):
        concepts = collections.defaultdict(list)

        for (form, c1, c2), occs in self._concordances[ctype].items():
            # get occurrence, and one example
            assert form
            concepts[c1].append((form, c2, len(occs)))

        return concepts

    def write_concepts(self, ctype, filename=None):
        concepts = self.get_concepts(ctype)
        with UnicodeWriter(filename, delimiter='\t') as w:
            w.writerow(
                ['ID', 'ENGLISH', 'OCCURRENCE', 'CONCEPT_IN_SOURCE', 'FORMS', 'PHRASE', 'GLOSS'])
            for i, (concept, forms) in enumerate(
                    sorted(concepts.items(), key=lambda x: x[1][0][-1], reverse=True), start=1):
                # Get the IGT containing the first occurrence listed in the concordance as example:
                igt = self[self._concordances[ctype][forms[0][0], concept, forms[0][1]][0][0]]
                w.writerow([
                    i,
                    concept,
                    sum([f[2] for f in forms]),
                    ' // '.join(sorted(set([f[1] for f in forms]))),
                    ' // '.join(sorted(set([f[0] for f in forms]))),
                    igt.phrase_text,
                    igt.gloss_text,
                ])
        if not filename:
            print(w.read().decode('utf8'))

    def check_glosses(self, level=2):
        count = 1
        for idx, igt in self._igts.items():
            if not igt.is_valid() and level >= 1:
                print('[{0} : first level {1}]'.format(idx, count))
                print(igt.phrase)
                print(igt.gloss_segmented)
                print('---')
                count += 1
            if level >= 2:
                for i, (w, m) in enumerate(zip(igt.phrase_segmented, igt.gloss_segmented), start=1):
                    if len(w) != len(m):
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
            tokenize = lingpy.ipa2tokens

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
        for ctype in ['lexicon', 'grammar']:
            concepts = self.get_concepts(ctype=ctype)
            concordance = self._concordances[ctype]
            for concept, entries in concepts.items():
                for form, cis, freq in entries:
                    # retrieve the concordance
                    pidx, sA, sB = concordance[form, concept, cis][0]
                    txt = self[pidx].phrase
                    gls = self[pidx].gloss
                    word, fgls = self[pidx, sA]
                    tokens = tokenize(form)
                    references = ' '.join(
                        ['{0}:{1}:{2}'.format(a, b, c)
                         for a, b, c in concordance[form, concept, cis]])
                    # check tokens
                    try:
                        lingpy.tokens2class(tokens, 'sca')
                        check = True
                    except:  # noqa: E722, # pragma: no cover
                        check = False
                    if concept.strip() and check:
                        D[idx] = [
                            doculect,
                            concept,
                            cis,
                            ctype,
                            form,
                            tokens,
                            freq,
                            word,
                            fgls,
                            txt,
                            gls,
                            references]
                        idx += 1
                    else:
                        print('[!] Problem with "{0}" / [{1}] [{2}] / {3} {4} {5}'.format(
                            concept,
                            form,
                            tokens,
                            pidx,
                            sA,
                            sB,
                        ))
        wl = lingpy.Wordlist(D)

        if lexstat:
            wl = lingpy.LexStat(D)
            wl.cluster(method='sca', threshold=threshold, ref=ref)
        else:
            wl.add_entries('cog', 'concept,form', lambda x, y: x[y[0]] + '-' + x[y[1]])
            wl.renumber('cog', ref)
        return wl

    def get_profile(self, clts=None, filename=None):
        """
        Compute an orthography profile with LingPy's function.

        :param filename: Write the computed profile to a file in addition to returning it.
        :return: `segments.Profile` instance.
        """
        clts = clts.bipa if clts else None

        D = {0: ['doculect', 'concept', 'ipa']}
        for i, key in enumerate(self._concordances.form, start=1):
            D[i] = ['dummy', key[1], key[0]]
        wordlist = lingpy.basic.wordlist.Wordlist(D)

        if not filename:
            with tempfile.NamedTemporaryFile(delete=FileExistsError) as fp:
                pass
            p = pathlib.Path(fp.name)
        else:
            p = pathlib.Path(filename)

        with UnicodeWriter(p, delimiter='\t') as w:
            w.writerow(['Grapheme', 'IPA', 'Example', 'Count', 'Unicode'])
            for line in lingpy.sequence.profile.context_profile(wordlist, ref='ipa', clts=clts):
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
