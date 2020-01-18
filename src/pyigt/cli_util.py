from clldutils.clilib import PathType

from pyigt import Corpus


def add_corpus(parser):
    parser.add_argument(
        'dataset',
        type=PathType('file'),
        help="Either a CLDF dataset specified by its metadata file or a CLDF ExampleTable"
             "as CSV file.")


def get_corpus(args):
    return Corpus.from_path(args.dataset)
