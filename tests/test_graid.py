import pytest

from pyigt.graid import GRAID, Boundary, Referent, Predicate, Symbol


@pytest.fixture(scope="session")
def graid():
    return GRAID()


@pytest.mark.parametrize(
    'expr,type_,res',
    [
        ('#nc', Symbol, None),
        # Examples from p. 26:
        ('#', Boundary, None),
        ('##', Boundary, None),
        ('#ds', Boundary, lambda b: b.ds),
        ('#rc.h:p', Boundary, None),
        ('#ds_rc', Boundary, None),
        ('#ac.neg', Boundary, None),
        ('#ds_cc.neg:p', Boundary, lambda b: b.ds and b.neg and b.clause_type == 'cc'),
        # Examples from p. 26:
        ('pro.h:s', Referent, lambda r: r.form_gloss == 'pro' and r.property == 'h' and r.function == 's'),
        ('aux', Predicate, None),
        ('v:pred', Predicate, lambda r: r.function == 'pred'),
        ('other', Symbol, None),
        ('=other', Symbol, None),
        ('vother', Predicate, None),
        ('=aux', Predicate, None),
        ('lv', Referent, None),
        ('0.h:a', Referent, None),
        #
        ('rn_refl_pro.h:poss', Referent, None),
        ('predex', Referent, lambda r: r.function == 'predex'),
        ('adp', Referent, None),
        ('=adp', Referent, None),
        ('voc', Referent, lambda r: r.form_gloss == None),
        ('-pro', Referent, lambda r: r.form_gloss == 'pro'),
        ('-v', Predicate, None),
    ]
)
def test_GRAID(graid, expr, type_, res):
    obj = graid.parse_expression(expr)
    assert obj.describe(graid)
    assert isinstance(obj, type_)
    if not res:
        assert str(obj) == expr
    else:
        assert res(obj)


@pytest.mark.parametrize(
    'kw,expr,res,exp',
    [
        # Basic errors:
        ({}, 'xx.1:s', None, ValueError),  # invalid form gloss
        ({}, 'dem_v:pred', None, ValueError),  # invalid soecified verb gloss
        ({}, 'x.x:s', None, ValueError),  # invalid referent property
        ({}, '##rc_xx', None, ValueError),  # invalid clause boundary symbol
        ({}, '##rc:xyz', None, ValueError),
        ({}, '##rc.z', None, ValueError),
        ({}, 'v:pred_dem', None, ValueError),
        ({}, 'v:prex', None, ValueError),
        (  # Custom specified form gloss:
            dict(form_glosses={'rex_f0': 'x', 'f0': 'y'}, form_gloss_specifiers={'abc': ''}),
            'abc_rex_f0:s',
            lambda r: r.form_gloss == 'f0',
            None),
        (  # Custom specified form gloss does not introduce a general specifier:
            dict(form_glosses={'rel_f0': 'x', 'f0': 'y'}), 'rel_pro:s', None, ValueError),
        (  # Custom specified predicate gloss:
            dict(predicate_glosses={'ds_v': 'x'}),
            'ds_v:pred',
            lambda r: isinstance(r, Predicate),
            None),
        (  # Custom specified function:
            dict(syntactic_functions={'a_ds': 'x'}),
            'pro.2:a_ds',
            lambda r: r.function == 'a' and r.function_qualifiers == ['ds'],
            None),
        (  # Custom specified function:
            dict(subconstituent_symbols={'dem': ('x', ['ln', 'rn'])}),
            'ln_dem',
            lambda r: r.subconstituent == 'ln' and r.subconstituent_qualifiers == ['dem'],
            None),
        (  # Custom specified function:
            dict(subconstituent_symbols={'aux': ('x', ['lv', 'rv'])}),
            'lv_aux',
            lambda r: r.subconstituent == 'lv' and r.subconstituent_qualifiers == ['aux'],
            None),
        (
            dict(clause_boundary_symbols={'dem': 'x'}, syntactic_function_specifiers={'dem': 'x'}),
            '#cc_dem:a_dem',
            lambda r: r.qualifiers == ['dem'],
            None),
        (
            dict(syntactic_function_specifiers={'dem': 'x'}),
            'pro.1:a_dem',
            lambda r: r.function_qualifiers == ['dem'],
            None),
        ({}, 'pro.1:a_dem', None, ValueError),
        (
            dict(with_cross_index=True),
            '-rn_pro_1_a',
            lambda r: r.function == 'a',
            None),
        (
            dict(other_symbols={'xyz': ''}),
            '-xyz',
            lambda r: r.symbol == 'xyz',
            None),
    ]
)
def test_custom_GRAID(kw, expr, res, exp):
    graid = GRAID(**kw)
    if exp:
        with pytest.raises(exp):
            graid.parse_expression(expr)
    else:
        obj = graid.parse_expression(expr)
        assert obj.describe(graid)
        assert str(obj) == expr
        if res:
            assert res(obj)


@pytest.mark.parametrize(
    'kw',
    [
        # Custom specified form gloss requires generic form gloss:
        dict(form_glosses={'rel_f0': 'x'}),
    ]
)
def test_invalid_GRAID_init(kw):
    with pytest.raises(AssertionError):
        GRAID(**kw)


def test_multiannotations(graid):
    assert len(graid('pro.2:s-aux')) == 2