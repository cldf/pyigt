import pytest

from pyigt.lgrmorphemes import *


def test_Infix():
    obj = Morpheme('<in>').elements[0]
    assert isinstance(obj, Infix)
    assert 'Infix' in repr(obj)


@pytest.mark.parametrize(
    'word,morphemes',
    [
        ('yerak~rak-im', 'yerak rak im'),
        ('b<um>i~bili', 'bi um bili'),
        ('reli<n>qu-ere', 'reliqu n ere'),
        ('palasi=lu', 'palasi lu'),
        ('abur-u-n', 'abur u n'),
        ('2DU>3SG-FUT-poke', '2DU>3SG FUT poke'),
        ('a-kolo<mu>ne=ta', 'a kolone mu ta'),
        ('1>3-see<2>=ERG', '1>3 see 2 ERG'),
    ]
)
def test_split_morphemes(word, morphemes):
    gw = GlossedWord(word=word, gloss=word)
    ms = []
    for gm in gw:
        f, i = gm.morpheme.form_and_infixes
        ms.append(f)
        ms.extend(i)
    assert ' '.join(ms) == morphemes


#def test_CorpusSpec_split_morphemes_invalid():
#    assert CorpusSpec().split_morphemes('a<b-c>d') == ['a<b', 'c>d']


#def test_CorpusSpec_split_morphemes_simple():
#    assert CorpusSpec(morpheme_separator='#').split_morphemes('a#d') == ['a', 'd']





@pytest.mark.parametrize(
    'gloss,grammar,lexicon',
    [
        ('get.dark:PRS', ['PRS'], ['get dark']),
        ('exist:REDUP:all', ['REDUP'], ['exist', 'all']),
        ('to.run;to_walk', [], ['to run', 'to walk']),
    ]
)
def test_GlossedMorpheme_concepts(gloss, grammar, lexicon):
    m = GlossedMorpheme(morpheme='m', gloss=gloss, sep='-')
    assert m.grammatical_concepts == grammar
    assert m.lexical_concepts == lexicon


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
    assert gw.form == 'insularum'
    assert gw[0].morpheme == 'insul'
    assert gw[0].first and gw[1].last
    for gm in gw:
        assert gm.morpheme and gm.gloss
