import re

from clldutils.lgr import ABBRS, PERSONS, pattern

__all__ = ['is_standard_abbr', 'expand_standard_abbr', 'is_generic_abbr']

STANDARD_ABBR_PATTERN = pattern()
GENERIC_ABBR_PATTERN = re.compile('^([A-Z][A-Z0-9]*|([1-3](DL|PL|SG|DU))|[1-3]/[1-3])$')


def is_generic_abbr(label):
    return bool((label in ABBRS) or GENERIC_ABBR_PATTERN.match(label))


def is_standard_abbr(label):
    match = STANDARD_ABBR_PATTERN.fullmatch(label)
    if match:
        return not bool(match.group('pre'))
    return False


def expand_standard_abbr(label):
    match = STANDARD_ABBR_PATTERN.fullmatch(label)
    if match and not match.group('pre'):
        res = ''
        if match.group('person'):
            res += PERSONS[match.group('person')] + ' '
        return res + ABBRS.get(match.group('abbr'))
    return label
