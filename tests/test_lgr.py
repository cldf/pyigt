import pytest

from pyigt import IGT
from pyigt.util import is_standard_abbr


def test_standard_abbrs():
    assert is_standard_abbr('1SG')
    assert not is_standard_abbr('A1SG')


def test_lgr_example(lgr_example):
    """
    Make sure we can round-trip all exmaples used in the LGR specification.
    """
    assert lgr_example.igt.is_valid(strict=True)
    for gw in lgr_example.igt.glossed_words:
        # Make sure we can roundtrip the string representations, thereby checking the parsing.
        assert gw.word_from_morphemes == gw.word
        assert gw.gloss_from_morphemes == gw.gloss


def test_rule1(lgr_examples):
    # Mereka  di  Jakarta sekarang.
    # They    in  Jakarta now
    igt = lgr_examples['1'].igt
    assert len(igt.gloss) == len(igt.phrase) == 4, 'Wrong number of words'


def test_rule2(lgr_examples, capsys):
    # Gila abur-u-n     ferma hamišaluǧ güǧüna amuq’-da-č.
    # now  they-OBL-GEN farm  forever   behind stay-FUT-NEG
    igt = lgr_examples['2'].igt
    igt.pprint()
    assert 'oblique' in capsys.readouterr()[0], 'Standard label not translated'

    # palasi=lu  niuirtur=lu
    # priest=and shopkeeper=and
    igt = lgr_examples['3'].igt
    assert len(igt.glossed_words[0]) == 2, 'Clitic not detected'


def test_rule3(lgr_examples):
    # My  s       Marko   poexa-l-i   avtobus-om  v   Peredelkino.
    # 1PL COM     Marko   go-PST-PL   bus-INS     All Peredelkino
    igt = lgr_examples['5a'].igt
    assert igt.gloss_abbrs['1PL'] == 'first person plural'


def test_rule4(lgr_examples):
    # insul-arum
    # island-GEN.PL
    igt = lgr_examples['7'].igt
    assert 'PL' in igt.gloss_abbrs, 'Period as gloss element separator not detected'

    # n=an        apedani     mehuni      essandu.
    # CONN=him    that.DAT.SG time.DAT.SG eat.they.shall
    # They shall celebrate him on that date. (CONN = connective)
    igt = lgr_examples['10'].igt
    assert igt.gloss_abbrs['CONN'] == 'connective'

    # çık-mak
    # come_out-INF
    igt = lgr_examples['12'].igt
    assert igt.glossed_words[0][0].gloss == 'come_out'

    # insul-arum
    # island-GEN;PL
    igt = lgr_examples['13'].igt
    assert 'PL' in igt.gloss_abbrs, 'Semicolon as gloss element separator not detected'

    # aux         chevaux
    # to;ART;PL   horse;PL
    igt = lgr_examples['14'].igt
    assert 'ART' in igt.gloss_abbrs

    # n=an        apedani     mehuni      essandu.
    # CONN=him    that:DAT;SG time:DAT;SG eat:they:shall
    igt = lgr_examples['15'].igt
    assert 'DAT' in igt.gloss_abbrs, 'Colon as gloss element separator not detected'

    # unser-n     Väter-n
    # our-DAT.PL father\PL-DAT
    igt = lgr_examples['16'].igt
    assert 'PL' in igt.gloss_abbrs, 'Backslash as gloss element separator not detected'

    # bhris-is
    # PST\break-2SG
    igt = lgr_examples['17'].igt
    assert 'PST' in igt.gloss_abbrs

    # mú-kòrà
    # SBJV\1PL-work
    igt = lgr_examples['18'].igt
    assert 'SBJV' in igt.gloss_abbrs

    # nanggayan   guny-bi-yarluga?
    # who         2DU>3SG-FUT-poke
    igt = lgr_examples['19'].igt
    assert '2DU' in igt.gloss_abbrs, '> as gloss element separator not detected'


def test_rule5(lgr_examples):
    # and-iamo
    # go-PRS.1.PL
    igt = lgr_examples['20'].igt
    assert '1' not in igt.gloss_abbrs

    # Rule 5A is hard to support.
    """
    Rule 5A. (Optional)

    Number and gender markers are very frequent in some languages, especially
    when combined with person. Several authors therefore use non-capitalized
    shortened abbreviations without a period. If this option is adopted, then the
    second gloss is used in (21).

    (21) Belhare
    ne-e    a-khim-chi      n-yuNNa
    DEM-LOC that.DAT.SG     3NSG-be.NPST
    DEM-LOC 1sPOSS-house-PL 3ns-be.NPST
    'Here are my houses.''
    """


def test_rule6(lgr_examples):
    # puer
    # boy[NOM.SG]
    igt1 = lgr_examples['22a'].igt
    assert 'NOM' in igt1.gloss_abbrs

    # puer-∅
    # boy-NOM.SG
    igt2 = lgr_examples['22b'].igt
    assert igt2.primary_text == 'puer'


def test_rule7(lgr_examples):
    # oz#-di-g    xõxe        m-uq'e-r
    # boy-OBL-AD  tree(G4)    COM-bend-PRET
    # 'Because of the boy the tree bent.' (G4 = 4th gender, PRET = preterite)")
    igt = lgr_examples['23'].igt
    assert igt.gloss_abbrs['G4'] == '4th gender'


def test_rule9(lgr_examples):
    # b<um>ili
    # <ACTFOC>buy
    igt = lgr_examples['27'].igt
    assert 'ACTFOC' in igt.gloss_abbrs

    # reli<n>qu-ere
    # leave<PRS>-INF
    igt = lgr_examples['28'].igt
    assert 'PRS' in igt.gloss_abbrs


def test_rule10(lgr_examples):
    # yerak~rak-im
    # green~ATT-M.PL
    igt = lgr_examples['29'].igt
    assert 'ATT' in igt.gloss_abbrs


def test_invalid(capsys):
    with pytest.raises(ValueError):
        IGT(phrase='a b', gloss='COM b c').check(strict=True, verbose=True)
    assert 'a\tb' in capsys.readouterr()[0]

    with pytest.raises(ValueError):
        IGT(phrase='x a-b-c', gloss='y COM-1SG').check(strict=True, verbose=True)
    assert 'a-b-c' in capsys.readouterr()[0]

    with pytest.raises(ValueError):
        IGT(phrase='a-bc', gloss='COM=1SG').check(strict=True, verbose=True)
    assert 'COM=1SG' in capsys.readouterr()[0]
