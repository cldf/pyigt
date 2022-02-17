from clldutils.lgr import ABBRS, PERSONS, pattern

__all__ = ['is_standard_abbr', 'expand_standard_abbr']

STANDARD_ABBR_PATTERN = pattern()


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
