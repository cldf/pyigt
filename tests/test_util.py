from pyigt.util import align


def test_align():
    assert align(['a', 'abc', '1'], ['123', 'a', 'x']) == """\
a      abc    1
123    a      x"""