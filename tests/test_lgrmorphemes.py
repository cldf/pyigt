from pyigt.lgrmorphemes import *


def test_Infix():
    obj = Morpheme('<in>').gloss_elements[0]
    assert isinstance(obj, Infix)
    assert 'Infix' in repr(obj)


def test_Morpheme_lexical_concepts():
    m = Morpheme('to.run;to_walk')
    assert m.lexical_concepts is None
    m.type = 'gloss'
    assert m.lexical_concepts == ['to run', 'to walk']


def test_agentlikeargument():
    m = Morpheme('COM>B')
    m.type = 'gloss'
    ges = m.gloss_elements
    assert len(ges) == 2
    assert ges[0].is_agentlike_argument
    assert ges[0].is_standard_abbreviation
    assert ges[1].is_category_label
    assert 'Morpheme' in repr(m)


def test_GlossedWord():
    gw = GlossedWord('insul-ar(u)m.', 'island-GEN;PL')
    assert len(gw.glossed_morphemes) == 2
    assert gw.stripped_word == 'insularum'
    assert gw.word_morphemes[0].first and gw.word_morphemes[1].last