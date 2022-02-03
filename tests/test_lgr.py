import pytest

from pyigt import IGT
from pyigt.igt import is_standard_abbr


def test_standard_abbrs():
    assert is_standard_abbr('1SG')
    assert not is_standard_abbr('A1SG')


def assert_is_valid(phrase, gloss, **kw):
    igt = IGT(phrase=phrase, gloss=gloss, **kw)
    assert igt.is_valid(strict=True)
    return igt


def test_rule1():
    """
    (1) Indonesian(Sneddon 1996: 237)

    Mereka  di  Jakarta sekarang.
    They    in  Jakarta now
    'They are in Jakarta now.'
    """
    igt = assert_is_valid('Mereka  di  Jakarta sekarang.', 'They    in  Jakarta now')
    assert len(igt.gloss) == 4


def test_rule2(capsys):
    igt = assert_is_valid(
        "Gila abur-u-n ferma hamišaluǧ güǧüna amuq’-da-č.",
        "now they-OBL-GEN farm forever behind stay-FUT-NEG")
    igt.pprint()
    assert 'oblique' in capsys.readouterr()[0]

    igt = assert_is_valid("palasi=lu niuirtur=lu", "priest=and shopkeeper=and")
    assert len(igt.glossed_morphemes[0][0]) == 2

    assert_is_valid("a-nii -láay", "3SG-laugh-FUT")


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


def test_rule3():
    igt = assert_is_valid(
        'My  s       Marko   poexa-l-i   avtobus-om  v   Peredelkino.',
        '1PL COM     Marko   go-PST-PL   bus-INS     All Peredelkino.')
    assert igt.gloss_abbrs['1PL'] == 'first person plural'

    igt = assert_is_valid(
        'My  s       Marko   poexa-l-i   avtobus-om  v   Peredelkino.',
        '1PL COM     Marko   go-PST-PL   bus-INS     All Peredelkino.',
        translation="'Marko and I went to Perdelkino by bus.' (COM=whatever)")
    assert igt.gloss_abbrs['COM'] == 'whatever'


def test_rule4():
    assert_is_valid('çık-mak', 'come.out-INF')

    igt = assert_is_valid('insul-arum', 'island-GEN.PL')
    assert 'PL' in igt.gloss_abbrs

    assert_is_valid('aux         chevaux', 'to.ART.PL   horse.PL')

    assert_is_valid('unser-n     Väter-n', 'our-DAT.PL  father.PL-DAT.PL')

    igt = assert_is_valid(
        'n=an        apedani     mehuni      essandu.',
        'CONN=him    that.DAT.SG time.DAT.SG eat.they.shall',
        translation="'They shall celebrate him on that date.' (CONN = connective)")
    assert igt.gloss_abbrs['CONN'] == 'connective'

    assert_is_valid('nanggayan   guny-bi-yarluga?', 'who         2DU.A.3SG.P-FUT-poke')

    igt = assert_is_valid('çık-mak', 'come_out-INF')
    assert igt.glossed_morphemes[0][0][1] == 'come_out'

    igt = assert_is_valid('insul-arum', 'island-GEN;PL')
    assert 'PL' in igt.gloss_abbrs

    igt = assert_is_valid('aux         chevaux', 'to;ART;PL   horse;PL')
    assert 'ART' in igt.gloss_abbrs

    igt = assert_is_valid(
        'n=an        apedani     mehuni      essandu.',
        'CONN=him    that:DAT;SG time:DAT;SG eat:they:shall')
    assert 'DAT' in igt.gloss_abbrs

    igt = assert_is_valid('unser-n     Väter-n', r'our-DAT.PL father\PL-DAT')
    assert 'PL' in igt.gloss_abbrs

    igt = assert_is_valid('bhris-is', r'PST\break-2SG')
    assert 'PST' in igt.gloss_abbrs

    igt = assert_is_valid('mú-kòrà', r'SBJV\1PL-work')
    assert 'SBJV' in igt.gloss_abbrs

    igt = assert_is_valid('nanggayan   guny-bi-yarluga?', 'who         2DU>3SG-FUT-poke')
    assert '2DU' in igt.gloss_abbrs


def test_rule5():
    igt = assert_is_valid('and-iamo', 'go-PRS.1.PL')
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


def test_rule6():
    igt1 = assert_is_valid('puer', 'boy[NOM.SG]')
    assert 'NOM' in igt1.gloss_abbrs
    igt2 = assert_is_valid('puer-∅', 'boy-NOM.SG')
    assert igt2.primary_text == 'puer'


def test_rule7():
    igt = assert_is_valid(
        "oz#-di-g    xõxe        m-uq'e-r",
        'boy-OBL-AD  tree(G4)    COM-bend-PRET',
        translation="'Because of the boy the tree bent.' (G4 = 4th gender, PRET = preterite)")
    assert igt.gloss_abbrs['G4'] == '4th gender'


def test_rule9():
    igt = assert_is_valid("b<um>ili", "<ACTFOC>buy")
    assert 'ACTFOC' in igt.gloss_abbrs

    igt = assert_is_valid("reli<n>qu-ere", "leave<PRS>-INF")
    assert 'PRS' in igt.gloss_abbrs


def test_rule10():
    igt = assert_is_valid("yerak~rak-im", "green~ATT-M.PL")
    assert 'ATT' in igt.gloss_abbrs
