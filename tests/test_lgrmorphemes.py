from pyigt.lgrmorphemes import *


def test_Infix():
    obj = Morpheme('<in>').elements[0]
    assert isinstance(obj, Infix)
    assert 'Infix' in repr(obj)


def test_Morpheme_lexical_concepts():
    m = GlossedWord('laufen', 'to.run;to_walk')
    assert m[0].lexical_concepts == ['to run', 'to walk']


def test_invalid_glossed_word():
    gw = GlossedWord('a-b-c', 'x-y', strict=False)
    assert not gw.is_valid
    assert len(gw) == 2
    gw = GlossedWord('a-b-c', 'x=y', strict=False)
    assert not gw.is_valid
    assert len(gw) == 1


def test_agentlikeargument():
    m = Morpheme('COM>B')
    m.type = 'gloss'
    ges = m.elements
    assert len(ges) == 2
    assert ges[0].is_agentlike_argument
    assert ges[0].is_standard_abbreviation
    assert ges[1].is_category_label
    assert 'Morpheme' in repr(m)


def test_GlossedWord():
    gw = GlossedWord('insul-ar(u)m.', 'island-GEN;PL')
    assert len(gw) == 2
    assert gw.stripped_word == 'insularum'
    assert gw[0].morpheme == 'insul'
    assert gw[0].first and gw[1].last
    for gm in gw:
        assert gm.morpheme and gm.gloss
