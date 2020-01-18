"""
Describe the IGTs in  a CLDF dataset
"""
from clldutils.clilib import Table

from pyigt.cli_util import add_corpus, get_corpus


def register(parser):
    add_corpus(parser)


def run(args):
    corpus = get_corpus(args)

    with Table('type', 'count') as t:
        e, w, m = corpus.get_stats()
        t.append(['example', e])
        t.append(['word', w])
        t.append(['morpheme', m])

    if e:
        print('\nExample properties:')
        for k in list(corpus.igts.values())[0].properties.keys():
            print('  ' + k)
