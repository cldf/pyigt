"""
Describe the IGTs in  a CLDF dataset
"""
from pycldf.cli_util import add_dataset, get_dataset
from clldutils.clilib import Table

from pyigt import Corpus


def register(parser):
    add_dataset(parser)


def run(args):
    corpus = Corpus(get_dataset(args))

    with Table('type', 'count') as t:
        e, w, m = corpus.get_stats()
        t.append(['example', e])
        t.append(['word', w])
        t.append(['morpheme', m])

    if e:
        print('\nExample properties:')
        for k in list(corpus.igts.values())[0].properties.keys():
            print('  ' + k)
