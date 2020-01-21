"""
List IGTs in a CLDF dataset
"""
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


def run(args):
    corpus = get_corpus(args)
    filters = [f.split('=', maxsplit=1) for f in args.filter]

    for igt in corpus:
        if (not filters) or all(p in str(igt.properties.get(c)) for c, p in filters):
            print('Example {0}:'.format(igt.id))
            print(igt)
            print()
