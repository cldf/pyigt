import re
import json
import pathlib
import operator
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
    morpheme_separator = attr.ib(
        validator=attr.validators.instance_of(str),
        default='-')
    label_pattern = attr.ib(default=re.compile('([A-Z]+|([1-3](dl|pl|sg|DL|PL|SG)))$'))

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
            or (ctype == 'lexicon' and not self.is_grammatical_gloss_label(g))]

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
    morpheme_separator = attr.ib(default='-')

    def __attrs_post_init__(self):
        self.phrase_segmented = [nfilter(m.split(self.morpheme_separator)) for m in self.phrase]
        self.gloss_segmented = [nfilter(m.split(self.morpheme_separator)) for m in self.gloss]

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
            return list(zip(self.phrase, self.gloss))[item]
        res = list(zip(self.phrase_segmented, self.gloss_segmented))[item[0]]
        return (res[0][item[1]], res[1][item[1]])

    def is_valid(self):
        return len(self.phrase) == len(self.gloss)

    @property
    def phrase_text(self):
        return ' '.join(self.phrase)

    @property
    def primary_text(self):
        return self.phrase_text.replace(self.morpheme_separator, '')

    @property
    def gloss_text(self):
        return ' '.join(self.gloss)


class Corpus(object):
    """
    A Corpus is an ordered list of `IGT` instances.
    """
    def __init__(self, igts, spec=None):
        self.spec = spec or CorpusSpec()
        self.igts = collections.OrderedDict([(igt.id, igt) for igt in igts])

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
                morpheme_separator=spec.morpheme_separator,
            )
            for igt in cldf['ExampleTable']]
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
        return len(self.igts)

    def __iter__(self):
        return iter(self.igts.values())

    def __getitem__(self, item):
        if not isinstance(item, tuple):
            return self.igts[item]
        if len(item) == 2:
            return self.igts[item[0]][item[1]]
        return self.igts[item[0]][tuple(item[1:])]

    def get_stats(self):
        wordc, morpc = 0, 0
        for igt in self.igts.values():
            for word in igt.phrase_segmented:
                wordc += 1
                morpc += len(word)
        return len(self.igts), wordc, morpc

    def get_concordance(self, ctype='grammar'):
        """
        Compute a morpheme- or gloss-level concordance of the corpus.

        :param ctype:
        :return:
        """
        con = collections.defaultdict(list)
        for idx, igt in self.igts.items():
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
                    if ctype == 'grammar':
                        for g in self.spec.grammatical_glosses(concept):
                            con[morpheme, g, concept].append(ref)
                    elif ctype == 'lexicon':
                        con[morpheme, self.spec.lexical_gloss(concept), concept].append(ref)
                    else:
                        con[morpheme, concept, concept].append(ref)
        return con

    def write_concordance(self, con, filename=None):
        with UnicodeWriter(filename, delimiter='\t') as w:
            w.writerow(['ID', 'FORM', 'GLOSS', 'GLOSS_IN_SOURCE', 'OCCURRENCE', 'REF'])
            for i, (k, v) in enumerate(
                    sorted(con.items(), key=lambda x: (-len(x[1]), x[0])), start=1):
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
        con = self.get_concordance(ctype=ctype)

        for (form, c1, c2), occs in con.items():
            # get occurrence, and one example
            assert form
            concepts[c1].append((form, c2, len(occs)))

        return concepts, con

    def write_concepts(self, concepts, con, filename=None):
        with UnicodeWriter(filename, delimiter='\t') as w:
            w.writerow(
                ['ID', 'ENGLISH', 'OCCURRENCE', 'CONCEPT_IN_SOURCE', 'FORMS', 'PHRASE', 'GLOSS'])
            for i, (concept, forms) in enumerate(
                    sorted(concepts.items(), key=lambda x: x[1][0][-1], reverse=True), start=1):
                w.writerow([
                    i,
                    concept,
                    sum([f[2] for f in forms]),
                    ' // '.join(sorted(set([f[1] for f in forms]))),
                    ' // '.join(sorted(set([f[0] for f in forms]))),
                    self[con[forms[0][0], concept, forms[0][1]][0][0]].phrase_text,
                    self[con[forms[0][0], concept, forms[0][1]][0][0]].gloss_text,
                ])
        if not filename:
            print(w.read().decode('utf8'))

    def check_glosses(self, level=2):
        count = 1
        for idx, igt in self.igts.items():
            if not igt.is_valid() and level >= 1:
                print('[{0} : first level {1]]'.format(idx, count))
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
            filename=False,
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
            concepts, concordance = self.get_concepts(ctype=ctype)
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
                    except:  # noqa: E722
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
                        print('[!] Problem with {0} / [{1}] / {2} {3} {4}'.format(
                            concept,
                            tokens,
                            pidx,
                            sA,
                            sB))
        wl = lingpy.Wordlist(D)

        if lexstat:
            wl = lingpy.LexStat(D)
            wl.cluster(method='sca', threshold=threshold, ref=ref)
        else:
            wl.add_entries('cog', 'concept,form', lambda x, y: x[y[0]] + '-' + x[y[1]])
            wl.renumber('cog', ref)
        return wl

    def get_profile(self, clts=None):
        """Compute an orthography profile with LingPy's function."""
        if clts:
            clts = clts.bipa

        concordance = self.get_concordance(ctype='forms')

        D = {0: ['doculect', 'concept', 'ipa']}
        for i, key in enumerate(concordance, start=1):
            D[i] = ['dummy', key[1], key[0]]
        wordlist = lingpy.basic.wordlist.Wordlist(D)

        return lingpy.sequence.profile.context_profile(wordlist, ref='ipa', clts=clts)

    def write_profile(self, profile, filename=None):
        with UnicodeWriter(filename, delimiter='\t') as w:
            w.writerow(['Grapheme', 'IPA', 'Example', 'Count', 'Unicode'])
            for line in profile:
                w.writerow([line[0], line[1], line[2], line[4], line[5]])
        if not filename:
            print(w.read())

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
        with pathlib.Path(dest).joinpath('script.js').open('w', encoding='utf8') as f:
            f.write('var WORDLIST = ' + json.dumps(WL, indent=2) + ';\n')
            f.write('var CONC = ' + json.dumps(CN, indent=2) + ';\n')
