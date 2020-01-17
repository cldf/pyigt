"""
List IGTs in a CLDF dataset
"""
from tabulate import tabulate
from pycldf.cli_util import add_dataset, get_dataset

from pyigt import Corpus


def register(parser):
    add_dataset(parser)
    parser.add_argument(
        '-c', '--column', help='column name to use for filter', default=None)
    parser.add_argument(
        '-m',
        '--match',
        metavar='PATTERN',
        default='',
        help='the string to search for')


def run(args):
    corpus = Corpus(get_dataset(args))

    for id, igt in corpus.igts.items():
        if (not args.column) or (args.match in igt.properties.get(args.column)):
            print('Example {0}:'.format(id))
            print(tabulate([igt.gloss], igt.phrase, tablefmt='plain'))
            print()
