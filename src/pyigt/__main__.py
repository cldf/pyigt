import sys
import contextlib

from clldutils.clilib import get_parser_and_subparsers, register_subcommands
from clldutils.loglib import Logging

import pyigt.commands


def main(args=None, catch_all=False, parsed_args=None):
    parser, subparsers = get_parser_and_subparsers('igt')
    register_subcommands(subparsers, pyigt.commands)

    args = parsed_args or parser.parse_args(args=args)

    if not hasattr(args, "main"):
        parser.print_help()
        return 1

    with contextlib.ExitStack() as stack:
        stack.enter_context(Logging(args.log, level=args.log_level))
        try:
            return args.main(args) or 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0
        except Exception as e:  # pragma: no cover
            if catch_all:
                print(e)
                return 1
            raise


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main() or 0)
