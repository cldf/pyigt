"""
Describe the IGTs in  a CLDF dataset
"""
from clldutils.clilib import Table

from pyigt.cli_util import add_corpus, get_corpus


def register(parser):
    add_corpus(parser)
    parser.add_argument('--verbose', action='store_true', default=False)


def run(args):
    corpus = get_corpus(args)

    with Table('type', 'count') as t:
        e, w, m = corpus.get_stats()
        t.append(['example', e])
        t.append(['word', w])
        t.append(['morpheme', m])

    if e:
        print('\nExample properties:')
        for igt in corpus:
            for k in igt.properties.keys():
                print('  ' + k)
            break

    if args.verbose:
        print('\nLGR Conformance:')
        for k, v in corpus.get_lgr_conformance_stats().most_common():
            print(k, v)
