import pathlib

import pytest

from pyigt.igt import *


@pytest.fixture
def corpus(dataset):
    return Corpus.from_cldf(dataset)


def test_IGT():
    from pyigt.lgrmorphemes import GlossedWord
    igt = IGT(id='1', phrase=['a-1', 'b-2', 'c-3'], gloss=['A-1', 'B-2', 'C-3'], properties={})
    assert len(igt) == 3
    for gw in igt:
        assert gw.word == 'a-1'
        break
    assert igt[1] == GlossedWord('b-2', 'B-2')
    assert 'B-2' in repr(igt[1])
    assert igt[0, 1].morpheme == '1'
    assert igt[0, 1].gloss == '1'
    assert [[repr(i) for i in l] for l in igt[2:, 1:]]
    assert igt.phrase_text == 'a-1 b-2 c-3'
    assert igt.primary_text == 'a1 b2 c3'
    assert igt.gloss_text == 'A-1 B-2 C-3'
    assert not IGT(id=1, phrase=[], gloss=['1'], properties={}).is_valid()


def test_IGT_conformance():
    assert IGT(phrase='a b', gloss='a').conformance == LGRConformance.UNALIGNED
    assert IGT(phrase='a b', gloss='a b-c').conformance == LGRConformance.WORD_ALIGNED
    assert IGT(phrase='a b=c', gloss='a b=c').conformance == LGRConformance.MORPHEME_ALIGNED


def test_IGT_words():
    igt = IGT(phrase='a=bcd -e', gloss='a=bcd-e', strict=True)
    assert igt.prosodic_words[0].word == 'a=bcd' == igt.prosodic_words[0].gloss
    assert igt.prosodic_words[1].word == 'e'
    assert igt.morphosyntactic_words[0].word == 'a' == igt.morphosyntactic_words[0].gloss
    assert igt.morphosyntactic_words[1].word == 'bcd -e'
    assert len(igt) != len(igt.as_prosodic())
    assert len(igt) != len(igt.as_morphosyntactic())


def test_IGT_malformed():
    igt = IGT(phrase='a--b', gloss='A--B')
    assert str(igt).startswith('ab')


def test_Corpus_from_path(fixtures):
    assert len(Corpus.from_path(fixtures / 'cldf-metadata.json')) == len(
        Corpus.from_path(str(fixtures / 'examples.csv')))


def test_Corpus_iter(corpus):
    for igt in corpus:
        assert isinstance(igt, IGT)


def test_Corpus_getitem(corpus):
    assert isinstance(corpus['1'], IGT)
    gw = corpus['1', 0]
    assert gw.word == 'zəp-le:' and gw.gloss == 'earth-DEF:CL'
    assert isinstance(corpus['1', 0:2], list)
    gm = corpus['1', 0, 1]
    assert gm.morpheme == 'le:' and gm.gloss == 'DEF:CL'


def test_Corpus_get_stats(corpus):
    e, w, m = corpus.get_stats()
    assert e == 5 and w == 17 and m == 36

    c = Corpus([IGT(id=1, phrase=['a', 'b-c'], gloss=['A'], properties={})])
    e, w, m = c.get_stats()
    assert e == 1 and w == 1 and m == 1


def test_Corpus_invalid_igts():
    c = Corpus([IGT(id=1, phrase='a b-c', gloss='a b--c')])
    assert not c.grammar


def test_Corpus_concordance_invalid():
    # Non-matching word and gloss
    c = Corpus([IGT(id=1, phrase=['a'], gloss=['1', 'A'], properties={})])
    assert not c.grammar

    # Non-matching morpheme and gloss
    c = Corpus([IGT(id=1, phrase=['a'], gloss=['A-B'], properties={})])
    assert not c.grammar

    # Valid:
    c = Corpus([IGT(id=1, phrase=['a'], gloss=['A'], properties={})])
    assert c.grammar

    # Empty morpheme:
    c = Corpus([IGT(id=1, phrase=['.'], gloss=['A'], properties={})])
    assert not c.grammar


def test_Corpus_write_concordance(corpus, capsys):
    corpus.write_concordance('grammar')
    out, _ = capsys.readouterr()
    assert 'CAUS' in out


def test_Corpus_write_concepts(corpus, capsys):
    corpus.write_concepts('lexicon')
    out, _ = capsys.readouterr()
    assert 'CAUS' in out


@pytest.mark.parametrize(
    'phrase,gloss,ctype,count,key',
    [
        ('a-b c', 'AB.CD.name-stuff other', 'lexicon', 3, 'name'),
        ('a-b c', 'AB.the_name-stuff other', 'lexicon', 3, 'the name'),
        ('a-b c', 'AB.CD.name-stuff other', 'grammar', 1, 'AB.CD'),
        ('a-b c', 'AB:CD.name-stuff other', 'grammar', 2, 'AB'),
        ('insul-arum', 'island-GEN;PL', 'grammar', 2, 'PL'),
        ('bhris-is', r'PST\break-2SG', 'grammar', 2, 'PST'),
        ('bhris-is', r'PST\break-2SG', 'lexicon', 2, 'break'),
        ('', '', 'lexicon', 17, 'burn'),
    ]
)
def test_Corpus_get_concepts(phrase, gloss, ctype, count, key, corpus):
    if phrase and gloss:
        corpus = Corpus([IGT(phrase=phrase.split(), gloss=gloss.split())])
    assert len(getattr(corpus, ctype)) == count
    assert key in getattr(corpus, ctype)


def test_check_glosses(capsys):
    corpus = Corpus([IGT(id=1, phrase=['a'], gloss=['1', 'A'], properties={})])
    corpus.check_glosses(level=2)
    out, _ = capsys.readouterr()

    corpus = Corpus([IGT(id=1, phrase=['a'], gloss=['A-B'], properties={})])
    corpus.check_glosses(level=2)
    out, _ = capsys.readouterr()


def test_get_wordlist(corpus, tmpdir, capsys, mocker):
    _ = corpus.get_wordlist()

    profile_path = pathlib.Path(str(tmpdir)) / 'profile.tsv'
    profile = corpus.get_profile(filename=profile_path)
    assert profile_path.exists()
    corpus.get_wordlist(profile=profile)

    _ = corpus.get_wordlist(lexstat=False, profile=corpus.get_profile())

    mocker.patch('pyigt.igt.lingpy', None)
    with pytest.raises(ValueError):
        _ = corpus.get_wordlist()


def test_write_app(corpus, tmpdir):
    dest = pathlib.Path(str(tmpdir))
    corpus.write_app(dest=dest)
    assert dest.joinpath('script.js').exists()
    assert dest.joinpath('index.html').exists()


def test_multilingual(multilingual_dataset, capsys):
    corpus = Corpus.from_cldf(multilingual_dataset)
    assert not corpus.monolingual
    assert len(set(igt.language for igt in corpus)) == 14

    corpus.write_concordance('lexicon')
    out, _ = capsys.readouterr()
    assert 'LANGUAGE_ID' in out

    corpus.write_concepts('grammar')
    out, _ = capsys.readouterr()
    assert 'macu1259: ' in out


def test_pkg_data():
    import pyigt

    assert pathlib.Path(pyigt.__file__).parent.joinpath('index.html').exists()
