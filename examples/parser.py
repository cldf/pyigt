from lingpy import *
from clldutils.text import strip_chars
from tabulate import tabulate

data = open('Qiang-2.txt').readlines()

D = {}
T = {}
idx = 1
start = True
previous = 0
for line in data:
    if line.startswith('Text'):
        text, title = line.split(': ')
        tidx = 1
        T[text] = {
                'title': title, 
                'idxs':[], 
                'words': [], 
                'glosses': [],
                'phrases': [],
                'sentences': [],
                'morphemes': [],
                'concepts': []
                }
        phrase, sentence = 1, 1
    elif line.strip():
        cells = line.split()
        if cells[0].isdigit():
            ipa = cells[1:]
            idis = cells[0]
            T[text]['idxs'] += [tidx for x in ipa]
            T[text]['words'] += ipa
            for word in ipa:
                w = strip_chars('“”', word)
                if w.endswith('.') or w.endswith('?') or w.endswith('!'):
                    sentence += 1
                elif w.endswith(',') or w.endswith(';'):
                    phrase += 1
                T[text]['sentences'] += [sentence]
                T[text]['phrases'] += [phrase]
                for char in '.,;?!':
                    w = w.strip(char)
                T[text]['morphemes'] += [w.split('-')]
            previous = len(ipa)
        else:
            gloss = cells
            if not previous == len(cells):
                print(text, idis)
                print(tabulate([
                    ipa,
                    gloss]))
                if len(gloss) < previous:
                    new_gloss = gloss + ['?', '?', '?']
                    new_gloss = new_gloss[:previous]
                    print(len(new_gloss), previous)
                    T[text]['glosses'] += new_gloss
                    T[text]['concepts'] += new_gloss
                else:
                    new_gloss = gloss[:previous]
                    print(len(new_gloss), previous)
                    new_gloss[-1] += '|'+'|'.join(gloss[previous:])
                    T[text]['glosses'] += new_gloss
                    T[text]['concepts'] += new_gloss
                previous = 0
            else:
                T[text]['glosses'] += gloss
                T[text]['concepts'] += [g.split('-') for g in gloss]
                previous = 0
    else:
        D[idx] = [text.strip(), title.strip(), tidx, idis, ' '.join(ipa), ' '.join(gloss)] 
        tidx += 1
        idx += 1

for text in T:
    if len(T[text]['glosses']) != len(T[text]['words']):
        print(text)

D[0] = ['text', 'title', 'line_id', 'id_in_source', 'ipa', 'gloss']
wl = Wordlist(D, col='text', row='title')

with open('qiang-igt.tsv', 'w') as f:
    count = 1
    f.write('\t'.join([
        'ID',
        'TEXT',
        'SENTENCE_ID',
        'PHRASE_ID',
        'PHRASE',
        'GLOSS'
        ])+'\n')
    for text, values in T.items():

        sl, pl, wl, gl, ml, cl = [], [], [], [], [], []
        current = 0
        for s, p, w, g, m, c in zip(
                T[text]['sentences'],
                T[text]['phrases'],
                T[text]['words'],
                T[text]['glosses'],
                T[text]['morphemes'],
                T[text]['concepts']):
            # start new
            if p != current:
                if current != 0:
                    f.write('\t'.join([
                        str(count),
                        text,
                        str(sl[0]),
                        str(basictypes.ints(pl)[0]),
                        ' '.join(wl),
                        ' '.join(gl),
                        #' _ '.join([' + '.join(m) for m in ml]),
                        #' _ '.join([' + '.join(g) for g in cl])
                        ])+'\n')
                    count += 1
               
                sl, pl, wl, gl, ml, cl = [], [], [], [], [], []
                sl += [s]
                pl += [p]
                wl += [w]
                gl += [g]
                ml += [m]
                cl += [c]
                current = p

            else:
                sl += [s]
                pl += [p]
                wl += [w]
                gl += [g]
                ml += [m]
                cl += [c]
        f.write('\t'.join([
            str(count),
            text,
            str(sl[0]),
            str(basictypes.ints(pl)[0]),
            ' '.join(wl),
            ' '.join(gl),
            #' _ '.join([' + '.join(m) for m in ml]),
            #' _ '.join([' + '.join(g) for g in cl])
            ])+'\n')

