import pathlib

import pytest
from csvw.dsv import reader

from pyigt import Corpus, IGT, LGRConformance


@pytest.fixture(scope='session')
def qiang():
    return pathlib.Path(__file__).parent / 'fixtures'/ 'qiang'


@pytest.fixture(scope='session')
def corpus(qiang):
    return Corpus([
        IGT(id=row['ID'], phrase=row['PHRASE'], gloss=row['GLOSS'])
        for row in reader(qiang / 'qiang-igt.tsv', delimiter='\t', dicts=True)
    ])


def test_conformance(corpus):
    assert corpus.get_lgr_conformance_stats()[LGRConformance.WORD_ALIGNED] == 14


def test_concordance(corpus, qiang, tmp_path):
    def items(p):
        res = set()
        for d in reader(pathlib.Path(p), delimiter='\t', dicts=True):
            del d['ID']
            res.add(tuple(d.values()))
        return res

    corpus.write_concordance('grammar', tmp_path / 'tmp.tsv')
    assert items(tmp_path / 'tmp.tsv') == items(qiang.joinpath(
        'output', 'grammatical-concordance.tsv'))

    corpus.write_concordance('lexicon', tmp_path / 'tmp.tsv')
    assert items(tmp_path / 'tmp.tsv') == items(qiang.joinpath(
        'output', 'lexical-concordance.tsv'))

    corpus.write_concordance('form', tmp_path / 'tmp.tsv')
    assert items(tmp_path / 'tmp.tsv') == items(qiang.joinpath(
        'output', 'form-concordance.tsv'))

    wl = corpus.get_wordlist()
    assert len(wl) == 1286
