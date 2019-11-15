import lingpy
from tabulate import tabulate
from collections import defaultdict
from clldutils.path import Path
try:
    from pyclts import CLTS
except:
    print('Warning CLTS missing')
from cldfcatalog import Catalog
from segments.tokenizer import Tokenizer
from clldutils.text import strip_chars
from lingpy import *
import json

def ilgt_path(*comps):
    return Path(__file__).parent.joinpath(*comps).as_posix()


class mlists(lingpy.basictypes.lists):

    def __init__(self, iterable, sep=" _ ", sepB=" + "):
        self.sep, self.sepB = sep, sepB
        lingpy.basictypes.lists.__init__(self, iterable, self.sep)
        for i in range(len(self.n)):
            self.n[i] = lingpy.basictypes.lists(self.n[i], self.sepB)

    def __getitem__(self, idx):
        if isinstance(idx, (list, tuple)) and len(idx) == 2:
            return self.n[idx[0]].n[idx[1]]
        return self.n[idx]


class Glosses(lingpy.basic.wordlist.Wordlist):

    def __init__(self, infile, row='text', col='sentence_id', phrase='phrase',
            gloss='gloss', conf=ilgt_path('conf',
                'ilgt.rc'), sep=' ', sepB='-'):
        lingpy.basic.wordlist.Wordlist.__init__(self, infile, row=row, col=col,
                conf=conf)
        self._gloss = gloss
        self._phrase = phrase
        for idx, gloss, phrase in self.iter_rows(gloss, phrase):
            self[idx, self._gloss] = mlists(gloss, sep, sepB)
            self[idx, self._phrase] = mlists(phrase, sep, sepB)

    def get_stats(self, tablefmt='pipe'):

        # count morphemes
        wordc, morpc = 0, 0
        for idx in self:
            words = self[idx, 'phrase']
            for word in words.n:
                wordc += 1
                for morpheme in word.n:
                    morpc += 1
        table = [['words', 'morphemes'], [wordc, morpc]]
        print(tabulate(table, tablefmt=tablefmt))

    def get_text(self, text, entry=False):
        """Shortcut to retrieve the entries of a given text."""
        idxs = self.get_list(row=text, flat=True)
        if not entry:
            return idxs
        return [self[idx, entry] for idx in idxs]

    def print_text(self, text, *entries, chunk=5, tablefmt='pipe'):
        idxs = self.get_list(row=text, flat=True)
        table = []
        for idx in idxs:
            tmp = [[] for x in entries]
            for i, entry in enumerate(entries):
                if isinstance(self[idx, entry], str):
                    entry = self[idx, entry].split()
                else:
                    entry = self[idx, entry]
                start = 0
                end = chunk
                while start < len(entry):
                    tmp[i] += [entry[start:end]]
                    start += chunk
                    end += chunk
            for i in range(len(tmp[0])):
                for j in range(len(entries)):
                    table += [tmp[j][i]]
                table += [['']]
        print(tabulate(table, tablefmt=tablefmt))

    def check_glosses(self, phrase='phrase', gloss='gloss', level=2):

        count = 1
        for idx, p, g in self.iter_rows(phrase, gloss):
            if len(p.n) != len(g.n) and level >= 1:
                print('[{0} : first level {1]]'.format(idx, count))
                print(p)
                print(g)
                print('---')
                count += 1
            for i, (w, m) in enumerate(zip(p.n, g.n)):
                if len(w.n) != len(m.n) and level >= 2:
                    print('[{0}:{1}:{2} : second level {3}]'.format(self[idx, 'text'], 
                        idx, i, count))
                    print(w)
                    print(m)
                    print('---')
                    count += 1
                    #input()

    def get_concordance(
            self,
            ctype='grammar',
            phrase='phrase',
            gloss='gloss',
            filename='concordance.tsv',
            markers=',;.”“"()',
            concept_replace=(('.', ' '), ('†(', ''), 
                ('†', '')),
            paradigm_marker=':',
            ):
        con = defaultdict(list)
        for idx, p, g in self.iter_rows(phrase, gloss):
            if len(p.n) == len(g.n):
                for i, (w, m) in enumerate(zip(p.n, g.n)):
                    if len(w.n) == len(m.n):
                        for j, (morpheme, concept) in enumerate(
                                zip(w.n, m.n)):
                            concept = str(concept)
                            morpheme = strip_chars(markers, str(morpheme))
                            if ctype == 'grammar':
                                if paradigm_marker in concept:
                                    bare_glosses = []
                                    for cn in concept.split(paradigm_marker):
                                        if cn.upper() == cn:
                                            bare_glosses += [cn]
                                    for g in bare_glosses:
                                        g_deriv = g
                                        for src, trg in concept_replace:
                                            g_deriv = g_deriv.replace(src, trg)
                                        if g_deriv.strip():
                                            con[morpheme, g_deriv, g] += [(idx,
                                                i, j)]      
                                elif concept.upper() == concept:
                                    con[morpheme, concept, concept] += [(idx, i,
                                        j)]
                            elif ctype == 'lexicon':
                                if paradigm_marker in concept:
                                    bare_gloss = []
                                    for cn in concept.split(paradigm_marker):
                                        if cn.upper() != cn:
                                            bare_gloss += [cn]
                                    bare_gloss = ' // '.join(bare_gloss)
                                    for src, trg in concept_replace:
                                        bare_gloss = bare_gloss.replace(src,
                                                trg)
                                    if bare_gloss.strip():
                                        con[morpheme, bare_gloss, concept] += [(idx, i, j)]
                                elif concept.upper() != concept:
                                    new_gloss = concept
                                    for src, trg in concept_replace:
                                        new_gloss = new_gloss.replace(src, trg)
                                    con[morpheme, new_gloss, concept] += [(idx, i, j)]
                            else:
                                con[morpheme, concept, concept] += [(idx, i, j)]
        table = []
        for i, (k, v) in enumerate(sorted(con.items(), key=lambda x: len(x[1]),
            reverse=True)):
            table += [[i+1, k[0], k[1], k[2], len(v), ' '.join(['{0}:{1}:{2}'.format(x, y, z) for
                x, y, z in v])]]
        if filename:
            with open(filename, 'w') as f:
                f.write('\t'.join(['ID', 'FORM', 'GLOSS', 'GLOSS_IN_SOURCE', 'OCCURRENCE',
                    'REF'])+'\n')
                for row in table:
                    f.write('\t'.join(['{0}'.format(x) for x in row])+'\n')
        if hasattr(self, 'concordance'):
            self.concordance[ctype] = con
            self.concordance_table[ctype] = table
        else:
            self.concordance = {ctype: con}
            self.concordance_table = {ctype: table}


    def get_concepts(
            self,
            ctype='lexicon',
            phrase='phrase',
            gloss='gloss',
            filename='concordance.tsv',
            markers=',;.”“"()?',
            concept_replace=(('.', ' '), ('†', '')),
            paradigm_marker=':',
            pprint=False
            ):
        
        if not hasattr(self, 'concordance'):
            self.get_concordance(ctype=ctype, phrase=phrase, gloss=gloss,
                    filename=False)
        if not 'forms' in self.concordance:
            self.get_concordance(ctype=ctype, phrase=phrase, gloss=gloss,
                    filename=False)
        concepts = defaultdict(list)
        for (form, c1, c2), occs in self.concordance[ctype].items():
            # get occurrence, and one example
            occ = len(occs)
            concepts[c1] += [(form, c2, occ)]
        # make a table
        table = [['ID', 'ENGLISH', 'OCCURRENCE', 'CONCEPT_IN_SOURCE', 'FORMS',
            ]]
            #'EXAMPLE_PHRASE']]
        for i, (concept, forms) in enumerate(sorted(concepts.items(), key=lambda x:
                x[1][0][-1], reverse=True)):
            table += [[
                i+1,
                concept,
                sum([f[2] for f in forms]),
                ' // '.join(sorted(set([f[1] for f in forms]))),
                ' // '.join(sorted(set([f[0] for f in forms]))),
                self[self.concordance[ctype][forms[0][0], concept, forms[0][1]][0][0], phrase],
                self[self.concordance[ctype][forms[0][0], concept, forms[0][1]][0][0], gloss]
                ]]
        if filename:
            with open(filename, 'w') as f:
                for line in table:
                    f.write('\t'.join([str(x) for x in line])+'\n')
        if pprint:
            print(tabulate(table, headers='firstrow', tablefmt='pipe'))

        try:
            self.concepts[ctype] = concepts
        except:
            self.concepts = {ctype: concepts}


    def get_wordlist(self, phrase='phrase', gloss='gloss', doculect='base',
            profile=False, filename=False, ref='crossid', lexstat=True,
            threshold=0.4):
        """
        Return a classical wordlist from the data.
        """

        # get the orthography profile
        if profile:
            profile = Tokenizer(profile)
            tokenize = lambda x: profile('^'+x+'$', column='IPA').split()
        else:
            tokenize = ipa2tokens
        if not hasattr(self, 'concepts'):
            self.get_concepts(ctype='lexicon', filename=False)
            self.get_concepts(ctype='grammar', filename=False)
        if not 'lexicon' in self.concepts or not 'grammar' in self.concepts:        
            self.get_concepts(ctype='lexicon', filename=False)
            self.get_concepts(ctype='grammar', filename=False)
        D = {0: ['doculect', 'concept', 'concept_in_source', 'concept_type', 'form',
            'tokens', 'occurrences', 'word_forms', 'gloss_forms', 'phrase_example',
            'gloss_example', 'references']}
        idx = 1
        for ctype in ['lexicon', 'grammar']:
            for concept, entries in self.concepts[ctype].items():
                for form, cis, freq in entries:
                    # retrieve the concordance
                    pidx, sA, sB = self.concordance[ctype][form, concept, cis][0]
                    txt = self[pidx, phrase]
                    gls = self[pidx, gloss]
                    word, fgls = txt[sA, :], gls[sA, :]
                    tokens = tokenize(form)
                    references = ' '.join(
                            ['{0}:{1}:{2}'.format(a, b, c) for a, b, c in
                                self.concordance[ctype][form, concept, cis]])
                    # check tokens
                    check = True
                    try:
                        tokens2class(tokens, 'sca')
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
        wl = Wordlist(D)
        export_columns = [h for h in wl.columns]+[ref]

        if lexstat:
            wl = LexStat(D)
            wl.cluster(method='sca', threshold=threshold, ref=ref)
        else:
            wl.add_entries('cog', 'concept,form', lambda x, y: x[y[0]]+'-'+x[y[1]])
            wl.renumber('cog', ref)
        if filename:
            wl.output('tsv', filename=filename, prettify=False, ignore='all',
                    subset=True, cols=export_columns)
        self.wordlist = wl

    def get_profile(self,
            phrase='phrase',
            gloss='gloss',
            context=True,
            filename='orthography.tsv',
            clts=True,
            clts_dir=None):
        """Compute an orthography profile with LingPy's function."""
        if clts:
            clts_dir = Catalog.from_config('clts').dir or Path(clts_dir)
            clts_ = CLTS(clts_dir)
            clts = clts_.bipa

        if not hasattr(self, 'concordance'):
            self.get_concordance(ctype='forms', phrase=phrase, gloss=gloss,
                    filename=False)
        if not 'forms' in self.concordance:
            self.get_concordance(ctype='forms', phrase=phrase, gloss=gloss,
                    filename=False)

        D = {0: ['doculect', 'concept', 'ipa']}
        for row in self.concordance_table['forms']:
            D[row[0]] = ['dummy', row[2], row[1]]
        wordlist = lingpy.basic.wordlist.Wordlist(D)

        profile = lingpy.sequence.profile.context_profile(
                wordlist,
                ref='ipa',
                clts=clts)
        with open(filename, 'w') as f:
            f.write('\t'.join(['Grapheme', 'IPA', 'Example', 'Count',
                'Unicode'])+'\n')
            for line in profile:
                f.write('\t'.join([line[0], line[1], line[2], line[4], line[5]])+'\n')

    def get_app(self, phrase='phrase', gloss='gloss', dest='app'):
        
        # idxs must be in index 2 of wordlist, form 0, and concept 1
        # concordance 0 is phrase, 1 is gloss
        
        WL, CN = {}, {}
        for idx, form, concept, refs in self.wordlist.iter_rows('form',
                'concept', 'references'):
            WL[idx] = [
                    form, 
                    concept, 
                    [[int(y) for y in x.split(':')] for x in refs.split()],
                    self.wordlist[idx, 'tokens'],
                    ]
            for line in WL[idx][2]:
                CN[line[0]] = [
                        self[line[0], phrase], 
                        self[line[0], gloss],
                        self[line[0], 'text'],
                        self[line[0], 'sentence_id'],
                        self[line[0], 'phrase_id']
                        ]
        with open(dest+'/script.js', 'w') as f:
            f.write('var WORDLIST = '+json.dumps(WL, indent=2)+';\n')
            f.write('var CONC = '+json.dumps(CN, indent=2)+';\n')

