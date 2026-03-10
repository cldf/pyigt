"""
Helpers for the `pyigt` CLI.
"""
import sys
import argparse

from clldutils.clilib import PathType

from pyigt import Corpus


def add_corpus(parser: argparse.ArgumentParser):
    """Add an argument to specify a CLDF Dataset."""
    parser.add_argument(
        'dataset',
        type=PathType(type='file', must_exist=False),
        help="Either a CLDF dataset specified by its metadata file or a CLDF ExampleTable"
             "as CSV file or '-' to read from <stdin>.")


def get_corpus(args: argparse.Namespace) -> Corpus:
    """Retrieve a Corpus according to the input from the CLI. Works in tandem with `add_corpus`."""
    if args.dataset.name == '-':
        return Corpus.from_stream(sys.stdin)
    return Corpus.from_path(args.dataset)
