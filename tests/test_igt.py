import pytest

from pyigt.igt import *


@pytest.fixture
def corpus(dataset):
    return Corpus(dataset)


def test_IGT():
    pass


def test_Corpus_get_stats(corpus):
    e, w, m = corpus.get_stats()
    assert e == 5 and w == 17 and m == 36


def test_Corpus_get_concepts(corpus):
    concepts, concordance = corpus.get_concepts()
    assert len(concepts) == 16
    assert len(concordance) == 16
