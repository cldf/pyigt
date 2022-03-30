import pathlib

import pytest

from pyigt.igt import *
from pyigt.igt import iter_morphemes


@pytest.fixture
def corpus(dataset):
    return Corpus.from_cldf(dataset)


@pytest.fixture
def corpus_spec():
    return CorpusSpec()


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
def test_CorpusSpec_split_morphemes(word, morphemes):
    assert ' '.join(CorpusSpec().split_morphemes(word)) == morphemes


def test_CorpusSpec_split_morphemes_invalid():
    assert CorpusSpec().split_morphemes('a<b-c>d') == ['a<b', 'c>d']


def test_CorpusSpec_split_morphemes_simple():
    assert CorpusSpec(morpheme_separator='#').split_morphemes('a#d') == ['a', 'd']


@pytest.mark.parametrize('gg', ['ABL', '2DL', 'ZZZ'])
def test_CorpusSpec_is_grammatical_gloss_label1(gg, corpus_spec):
    assert corpus_spec.is_grammatical_gloss_label(gg)


@pytest.mark.parametrize('gg', ['stone', '1Pl'])
def test_CorpusSpec_is_grammatical_gloss_label2(gg, corpus_spec):
    assert not corpus_spec.is_grammatical_gloss_label(gg)


@pytest.mark.parametrize('i,o', [('something."', "something")])
def test_CorpusSpec_strip_punctuation(i, o, corpus_spec):
    assert corpus_spec.strip_punctuation(i) == o


def test_CorpusSpec_grammatical_glosses(corpus_spec):
    assert corpus_spec.grammatical_glosses('get.dark:PRS') == ['PRS']
    assert corpus_spec.grammatical_glosses('exist:REDUP:all') == ['REDUP']


def test_CorpusSpec_lexical_gloss(corpus_spec):
    assert corpus_spec.lexical_gloss('get.dark:PRS') == 'get dark'
    assert corpus_spec.lexical_gloss('exist:REDUP:all') == 'exist // all'


def test_IGT():
    igt = IGT(id='1', phrase=['a-1', 'b-2', 'c-3'], gloss=['A-1', 'B-2', 'C-3'], properties={})
    assert igt[1] == ('b-2', 'B-2')
    assert igt[0, 1] == ('1', '1')
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
    assert corpus['1', 0] == ('zəp-le:', 'earth-DEF:CL')
    assert corpus['1', 0, 1] == ('le:', 'DEF:CL')


def test_Corpus_get_stats(corpus):
    e, w, m = corpus.get_stats()
    assert e == 5 and w == 17 and m == 36

    c = Corpus([IGT(id=1, phrase=['a', 'b-c'], gloss=['A'], properties={})])
    e, w, m = c.get_stats()
    assert e == 1 and w == 2 and m == 3


def test_Corpus_invalid_igts():
    c = Corpus([IGT(id=1, phrase='a b-c', gloss='a b--c')])
    assert not c.get_concepts()


def test_Corpus_concordance_invalid():
    # Non-matching word and gloss
    c = Corpus([IGT(id=1, phrase=['a'], gloss=['1', 'A'], properties={})])
    assert not c._concordances['grammar']

    # Non-matching morpheme and gloss
    c = Corpus([IGT(id=1, phrase=['a'], gloss=['A-B'], properties={})])
    assert not c._concordances['grammar']

    # Valid:
    c = Corpus([IGT(id=1, phrase=['a'], gloss=['A'], properties={})])
    assert c._concordances['grammar']

    # Empty morpheme:
    c = Corpus([IGT(id=1, phrase=['.'], gloss=['A'], properties={})])
    assert not c._concordances['grammar']


def test_Corpus_write_concordance(corpus, capsys):
    corpus.write_concordance('grammar')
    out, _ = capsys.readouterr()
    assert 'CAUS' in out


def test_Corpus_concepts(corpus, capsys):
    concepts = corpus.get_concepts()
    assert len(concepts) == 17
    corpus.write_concepts('lexicon')
    out, _ = capsys.readouterr()
    assert 'CAUS' in out


def test_check_glosses(capsys):
    corpus = Corpus([IGT(id=1, phrase=['a'], gloss=['1', 'A'], properties={})])
    corpus.check_glosses(level=2)
    out, _ = capsys.readouterr()

    corpus = Corpus([IGT(id=1, phrase=['a'], gloss=['A-B'], properties={})])
    corpus.check_glosses(level=2)
    out, _ = capsys.readouterr()


def test_get_wordlist(corpus, tmpdir, capsys):
    _ = corpus.get_wordlist()

    profile_path = pathlib.Path(str(tmpdir)) / 'profile.tsv'
    profile = corpus.get_profile(filename=profile_path)
    assert profile_path.exists()
    corpus.get_wordlist(profile=profile)

    _ = corpus.get_wordlist(lexstat=False, profile=corpus.get_profile())


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


def test_iter_morphemes():
    assert list(iter_morphemes('<a>-b=c~d', split_infixes=False)) == [
        (None, '<a>'), ('-', 'b'), ('=', 'c'), ('~', 'd')]
