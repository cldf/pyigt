"""
List IGTs in a CLDF dataset
"""
from pyigt.cli_util import add_corpus, get_corpus


def register(parser):
    add_corpus(parser)
    parser.add_argument(
        '-c', '--column', help='column name to use for filter', default=None)
    parser.add_argument(
        '-m',
        '--match',
        metavar='PATTERN',
        default='',
        help='the string to search for')


def run(args):
    corpus = get_corpus(args)
    for id, igt in corpus.igts.items():
        if (not args.column) or (args.match in igt.properties.get(args.column)):
            print('Example {0}:'.format(id))
            print(igt)
            print()
