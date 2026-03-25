"""
Utility functions.
"""
import re
import itertools

from clldutils.lgr import ABBRS, PERSONS, pattern

__all__ = ['is_standard_abbr', 'expand_standard_abbr', 'is_generic_abbr', 'align']

STANDARD_ABBR_PATTERN = pattern()
GENERIC_ABBR_PATTERN = re.compile('^([A-Z][A-Z0-9]*|([1-3](DL|PL|SG|DU))|[1-3]/[1-3])$')


def align(seq1, seq2) -> str:
    """Align the words in seq1 and seq2."""
    line1, line2 = [], []
    for w1, w2 in itertools.zip_longest(seq1, seq2, fillvalue=''):
        w1 = w1.strip()
        w2 = w2.strip()
        maxlen = max((len(w1), len(w2)))
        line1.append(w1.ljust(maxlen))
        line2.append(w2.ljust(maxlen))
    return '\n'.join(['    '.join(line1), '    '.join(line2)])


def is_generic_abbr(label: str) -> bool:
    """
    >>> is_generic_abbr('ABC')
    True
    >>> is_generic_abbr('abc')
    False
    """
    return bool((label in ABBRS) or GENERIC_ABBR_PATTERN.match(label))


def is_standard_abbr(label: str) -> bool:
    """
    >>> is_standard_abbr('ABC')
    False
    >>> is_standard_abbr('DU')
    True
    """
    match = STANDARD_ABBR_PATTERN.fullmatch(label)
    if match:
        return not bool(match.group('pre'))
    return False


def expand_standard_abbr(label: str) -> str:
    """
    >>> expand_standard_abbr('DU')
    'dual'
    """
    match = STANDARD_ABBR_PATTERN.fullmatch(label)
    if match and not match.group('pre'):
        res = ''
        if match.group('person'):
            res += PERSONS[match.group('person')] + ' '
        return res + ABBRS.get(match.group('abbr'))
    return label
