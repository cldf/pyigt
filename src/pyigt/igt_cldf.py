import json
import pathlib
import operator
import collections

import lingpy
import segments
import attr
from tabulate import tabulate
from clldutils.text import strip_chars
from clldutils.misc import nfilter
from csvw.dsv import UnicodeWriter


@attr.s
class IGT(object):
    id = attr.ib()
    phrase = attr.ib(validator=attr.validators.instance_of(list))
    gloss = attr.ib(validator=attr.validators.instance_of(list))
    morpheme_separator = attr.ib(default='-')

    def __attrs_post_init__(self):
        self.phrase_segmented = [nfilter(m.split(self.morpheme_separator)) for m in self.phrase]
        self.gloss_segmented = [nfilter(m.split(self.morpheme_separator)) for m in self.gloss]

    def __getitem__(self, item):
        if not isinstance(item, tuple):
            return list(zip(self.phrase, self.gloss))[item]
        return list(zip(self.phrase_text, self.gloss_segmented))[item[0]][item[1]]

    def is_valid(self):
        return len(self.phrase) == len(self.gloss)

    @property
    def phrase_text(self):
        return ' '.join(self.phrase)

    @property
    def gloss_text(self):
        return ' '.join(self.gloss)


class Glosses2(object):
    def __init__(self, cldf):
        _id = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#id'].name
        _phrase = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#analyzedWord'].name
        _gloss = cldf['ExampleTable', 'http://cldf.clld.org/v1.0/terms.rdf#gloss'].name
        self._igts = collections.OrderedDict([
            (igt[_id], IGT(id=igt[_id], gloss=igt[_gloss], phrase=igt[_phrase]))
            for igt in cldf['ExampleTable']])

    def __getitem__(self, item):
        if not isinstance(item, tuple):
            return self._igts[item]
        return self._igts[item[0]][tuple(item[1:])]

    def get_stats(self, tablefmt='pipe'):
        wordc, morpc = 0, 0
        for igt in self._igts.values():
            for word in igt.phrase_segmented:
                wordc += 1
                morpc += len(word)
        table = [['words', 'morphemes'], [wordc, morpc]]
        print(tabulate(table, tablefmt=tablefmt))

    def get_concordance(
            self,
            ctype='grammar',
            markers=',;.”“"()',
            concept_replace=(('.', ' '), ('†(', ''), ('†', '')),
            paradigm_marker=':',
    ):
        def _glosses(concept):
            op = operator.eq if ctype == 'grammar' else operator.ne
            return [cn for cn in concept.split(paradigm_marker) if op(cn.upper(), cn)]

        con = collections.defaultdict(list)
        for idx, igt in self._igts.items():
            if not igt.is_valid():
                continue
            for i, (w, m) in enumerate(zip(igt.phrase_segmented, igt.gloss_segmented)):
                if len(w) != len(m):
                    continue
                for j, (morpheme, concept) in enumerate(zip(w, m)):
                    morpheme = strip_chars(markers, morpheme)
                    ref = (idx, i, j)
                    if ctype == 'grammar':
                        if paradigm_marker in concept:
                            for g in _glosses(concept):
                                g_deriv = g
                                for src, trg in concept_replace:
                                    g_deriv = g_deriv.replace(src, trg)
                                if g_deriv.strip():
                                    con[morpheme, g_deriv, g].append(ref)
                        elif concept.upper() == concept:
                            con[morpheme, concept, concept].append(ref)
                    elif ctype == 'lexicon':
                        if paradigm_marker in concept:
                            bare_gloss = ' // '.join(_glosses(concept))
                            for src, trg in concept_replace:
                                bare_gloss = bare_gloss.replace(src, trg)
                            if bare_gloss.strip():
                                con[morpheme, bare_gloss, concept] .append(ref)
                        elif concept.upper() != concept:
                            new_gloss = concept
                            for src, trg in concept_replace:
                                new_gloss = new_gloss.replace(src, trg)
                            con[morpheme, new_gloss, concept].append(ref)
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
        for idx, igt in self._igts.items():
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
            tokenize = lambda x: profile('^' + x + '$', column='IPA').split()
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
                    txt = self._igts[pidx].phrase
                    gls = self._igts[pidx].gloss
                    word, fgls = txt[sA - 1, :], gls[sA - 1, :]
                    tokens = tokenize(form)
                    references = ' '.join(
                        ['{0}:{1}:{2}'.format(a, b, c)
                         for a, b, c in concordance[form, concept, cis]])
                    # check tokens
                    try:
                        lingpy.tokens2class(tokens, 'sca')
                        check = True
                    except:
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

    def get_app(self, dest='app'):
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
