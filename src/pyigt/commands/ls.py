"""
List IGTs in a CLDF dataset
"""
import re

from pyigt.cli_util import add_corpus, get_corpus


def register(parser):
    add_corpus(parser)
    parser.add_argument(
        'filter',
        nargs='*',
        help='filter condition in the form "COLUMN NAME=PATTERN". '
             'Run "igt stats" for a list of available column names.',
        metavar='FILTER',
    )
    parser.add_argument(
        '-r', '--regex',
        help="treat filter patterns as regular expressions",
        action='store_true',
        default=False,
    )


def run(args):
    corpus = get_corpus(args)
    filters = [f.split('=', maxsplit=1) for f in args.filter]

    if args.regex:
        filters = [(c, re.compile(p)) for c, p in filters]

    def match(igt, c, p):
        v = igt.properties.get(c)
        if args.regex:
            if isinstance(v, list):
                return any(p.search(vv or '') for vv in v)
            return p.search(v or '')
        if isinstance(v, list):
            return any(p in vv for vv in v)
        return p in v

    for igt in corpus:
        if (not filters) or all(match(igt, c, p) for c, p in filters):
            print('Example {0}:'.format(igt.id))
            print(igt)
            print()

    if corpus.fname:
        print('IGT corpus at {0}'.format(corpus.fname))
