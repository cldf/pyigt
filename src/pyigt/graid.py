"""
Module implementing the GRAID 7.0 specification.

https://multicast.aspra.uni-bamberg.de/data/pubs/graid/Haig+Schnell2014_GRAID-manual_v7.0.pdf
"""
import re
import typing
import itertools
import collections
import dataclasses

__all__ = ['Referent', 'Boundary', 'Predicate', 'Symbol', 'GRAID']

SymbolDict = typing.Dict[typing.Union[typing.Tuple[str, str], str], str]


def update_symbols(symbols: SymbolDict,
                   d: SymbolDict,
                   attaches: typing.Union[typing.Literal['left'], typing.Literal['right']] = None):
    if d:
        assert all(isinstance(g, str) and g.count('_') < 2 if attaches else 1 for g in d)
        if attaches:
            symbols.update({tuple(k.split('_')) if '_' in k else k: v for k, v in d.items()})
            assert all(
                isinstance(k, str) or (k[1] if attaches == 'left' else k[0]) in symbols
                for k in symbols), (
                'Core component of composite symbol is not a generic symbol: {}'.format(symbols))
        else:
            symbols.update(d)


def re_or(items: typing.Iterable[str]) -> str:
    return r'|'.join(re.escape(item) for item in items)


class GRAID:
    """
    The GRAID 7.0 specification.
    """
    def __init__(self,
                 form_glosses: SymbolDict = None,
                 form_gloss_specifiers: SymbolDict = None,
                 referent_properties: SymbolDict = None,
                 syntactic_functions: SymbolDict = None,
                 predicate_glosses: SymbolDict = None,
                 clause_boundary_symbols: SymbolDict = None,
                 subconstituent_symbols: typing.Dict[str, typing.Tuple[str, list]] = None,
                 other_symbols: SymbolDict = None):
        """
        Basically all lists of symbols specified by the GRAID standard may be extended with new,
        corpus-specific symbols. Such custom symbols can be supplied as values for the arguments
        of this method as follows: For all but `subconstituent_symbols` the symbols should be
        formatted as `dict` mapping each symbol to a short description. Symbols should generally
        be composed of lowercase ASCII letters, but may contain an underscore. If so, they are
        interpreted as (specifier, gloss) pairs. E.g. a cuśtom symbol `"rel_pro"` specified for
        `form_glosses` will allow parsing of a GRAID annotation `rel_pro.1:s`, but not of
        `rel_np.1:s`. To specify a generic form gloss specifier `rel`, it would need to be passed
        as `form_gloss_specifiers` argument.

        :param form_glosses: Custom form gloss symbols. See Table 1 of the spec for the defaults.
        :param form_gloss_specifiers: Custom form gloss specifiers.
        :param referent_properties: Custom referent properties. See Table 2 for the defaults.
        :param syntactic_functions: Custom syntactic function symbols. See Table 3 for the defaults.
        :param predicate_glosses: Custom predicate gloss symbols. See the form glosses in Table 4 \
        for the defaults.
        :param clause_boundary_symbols: Custom clause boundary symbols. See the clause operators in\
        Table 5 for the defaults.
        :param subconstituent_symbols: Sometimes more detailed glossing of (verb complex or noun \
        phrase) subconstituents is needed. Symbols for this can be specified as `dict` mapping the \
        symbol to a pair (description, list of subconstituent markers it attaches to). E.g. a \
        subconstituent symbol `dem` for noun phrases can be specified as \
        `{"dem": ("adnomoinal demonstrative", ["ln", "rn"])}`
        :param other_symbols: Custom, additional symbols. These symbols will only be recognized if \
        they appear by themselves, possibly prefixed with a morpheme separator.
        """
        # Morpheme separators and how they translate to boundedness
        self.morpheme_separators = collections.OrderedDict([("-", "bound"), ("=", "clitic")])

        # Glossing of forms:
        self.form_glosses = {  # Spec Table1.
            'np': 'noun phrase',
            'pro': 'free pronoun in full form',
            ('=', 'pro'): "‘weak’ clitic pronoun",
            ('-', 'pro'): 'pronominal affix, cf. Section 3',
            '0': 'covert argument / phonologically null argument',
            'refl': 'reflexive or reciprocal pronoun, cf. Section 4.2',
            'adp': 'adposition',
            'x': '’non-referential’, see below for explanation',
            'other': 'used for expressions 1) that are not of a type listed above 2) the form of '
                     'which is not considered relevant',
        }
        update_symbols(self.form_glosses, form_glosses, 'left')
        self.form_gloss_prefixes = {
            'w': '‘weak’ (optional symbol), indicates a phonologically lighter form, it precedes '
                 'the form symbol, e.g. <wpro>',
        }
        self.form_gloss_specifiers = form_gloss_specifiers or {}
        self.syntactic_functions = {  # Table 3.
            's': 'intransitive subject',
            'S': 'intransitive subject',
            'a': 'transitive subject',
            'A': 'transitive subject',
            'p': 'transitive object',
            'P': 'transitive object',
            'ncs': 'non-canonical subject',
            'g': 'goal argument of a goal-oriented verb of motion, but also: recipient of verb '
                 'of transfer, and addressee of verb of speech',
            'l': 'locative argument of verbs of location',
            'obl': 'oblique argument, excluding goals and locatives',
            'p2': 'secondary object',
            'dt': 'dislocated topic (right or left-dislocated)',
            'voc': 'vocative',
            'poss': 'possessor',
            'appos': 'appositional',
            'other': 'other function',
        }
        update_symbols(self.syntactic_functions, syntactic_functions, 'right')
        self.predicate_glosses = {
            'v': 'verb or verb complex (cf. Section 2.5.1)',
            'vother': 'non-canonical verb-form (cf. Section 2.5.5)',
            'cop': '(overt) copular verb (cf. Section 2.5.2)',
            'aux': 'auxiliary (cf. Section 2.5.2)',
            ('-', 'aux'): 'suffixal auxiliary',
            ('=', 'aux'): 'clitic auxiliary',
        }
        update_symbols(self.predicate_glosses, predicate_glosses, 'left')

        self.predicative_functions = {
            'pred': 'predicative function',
            'predex': 'predicative function in existential / presentational constructions',
        }
        # Glossing of referent properties, see spec Table 2
        self.referent_properties = {
            '1': '1st person referent(s)',
            '2': '2nd person referent(s)',
            'h': 'human referent(s)',
            'd': 'anthropomorphized referent(s); the use of this symbol is optional',
        }
        self.referent_properties.update(referent_properties or {})
        # Glossing of clause boundaries:
        self.boundary_markers = {
            '##': 'boundary of independent clause, inserted at left edge',
            '#': 'boundary of dependent clause, inserted at left edge, further specified',
            '%': 'end of a dependent clause (if not coinciding with the end if its main clause)',
        }
        self.clause_types = {
            'rc': 'relative clause',
            'cc': 'complement clause',
            'ac': 'adverbial clause',
        }
        # Some corpora specify additional symbols to qualify clause boundaries.
        self.clause_boundary_symbols = clause_boundary_symbols or {}
        # Misc glossing:
        self.subconstituent_markers = {  # Spec Table 1.
            'ln': 'NP-internal subconstituent occurring to the left of NP head',
            'rn': 'NP-internal subconstituent occurring to the right of NP head',
            'lv': 'subconstituent of verb complex occurring to the left of verbal head',
            'rv': 'subconstituent of verb complex occurring to the right of verbal head',
        }
        self.subconstituent_symbols = collections.defaultdict(dict)
        if subconstituent_symbols:
            for k, (desc, attaches_to) in subconstituent_symbols.items():
                for ato in attaches_to:
                    assert ato in self.subconstituent_markers
                    self.subconstituent_symbols[ato][k] = desc
        self.other_symbols = {
            'other': 'forms / words / elements which are not relevant for the analysis',
            'nc': '‘not considered’ / ‘non-classifiable’',
        }
        update_symbols(self.other_symbols, other_symbols)

    def iter_expressions(self, s):
        sep = None
        for item in itertools.dropwhile(
                lambda ss: not ss, re.split(r'({})'.format(re_or(self.morpheme_separators)), s)):
            if item in self.morpheme_separators:
                sep = item
            else:
                assert item
                yield '{}{}'.format(sep if sep else '', item)
                sep = None
        assert not sep, 'Trailing morpheme separator in gloss: {}'.format(s)

    def __call__(self, gloss):
        return [self.parse_expression(exp) for exp in self.iter_expressions(gloss.strip())]

    def parse_expression(self, expression):
        #
        # FIXME: try custom glosses first!
        #

        if re.fullmatch(r'({})?({})'.format(
                re_or(self.morpheme_separators), re_or(self.other_symbols)), expression):
            return Symbol(expression)

        for bm in self.boundary_markers:
            if expression.startswith(bm):
                if expression == bm + 'nc':
                    return Symbol(expression)
                return Boundary.from_annotation(expression, bm, parser=self)

        if expression in self.syntactic_functions:
            expression = ':' + expression

        if expression in self.predicative_functions:
            expression = ':' + expression

        form, _, func = expression.partition(':')
        if any(form.startswith(sep) for sep in self.morpheme_separators):
            form = form[1:]
        form_comps = form.split('_')
        if form_comps[-1] in self.predicate_glosses or tuple(form_comps[-2:]) in self.predicate_glosses:
            return Predicate.from_annotation(expression, parser=self)

        return Referent.from_annotation(expression, parser=self)


DEFAULT_PARSER = GRAID()


@dataclasses.dataclass
class Symbol:
    symbol: str

    def __str__(self):
        return self.symbol

    @classmethod
    def from_annotation(cls, annotation, parser):  # pragma: no cover
        return cls(annotation)


#
# Allow custom elements
#
class CustomGloss:  # Implement cross-index as example!
    #CROSS_INDEX_PATTERN = re.compile(r'(-|=)?((l|r)v_)?pro_[a-z12]+_[a-z]+')
    @classmethod
    def from_annotation(cls, annotation: str, parser=None):  # pragma: no cover
        return cls()


@dataclasses.dataclass
class Boundary:
    boundary_type: str
    clause_type: str = None
    ds: bool = False
    neg: bool = False
    property: str = None
    function: str = None
    qualifiers: typing.List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_annotation(cls, annotation: str, marker: str, parser=None) -> "Boundary":
        parser = parser or DEFAULT_PARSER
        kw = {'qualifiers': [], 'boundary_type': marker}
        rem, _, kw['function'] = annotation[len(kw["boundary_type"]):].partition(":")
        if kw['function']:
            if ((kw['function'] not in parser.predicative_functions) and
                    (kw['function'] not in parser.syntactic_functions)):
                raise ValueError(annotation)
        else:
            kw['function'] = None
        if rem:
            if rem.endswith('.neg'):
                rem = rem[:-len('.neg')]
                kw['neg'] = True
            else:
                rem, _, prop = rem.partition(".")
                if prop:
                    if prop not in parser.referent_properties:
                        raise ValueError(annotation)
                    kw['property'] = prop
        if rem:
            comps = set(rem.split('_'))
            for a in ['ds', 'neg']:
                # Note: We also recognize '_neg', although the spec says it must be '.neg'.
                kw[a] = kw.get(a) or (a in comps)
                comps.discard(a)
            for ct in parser.clause_types:
                if ct in comps:
                    kw['clause_type'] = ct
                    comps.remove(ct)
            for comp in comps:
                if comp in parser.clause_boundary_symbols:
                    kw['qualifiers'].append(comp)
                else:
                    raise ValueError(annotation)
            kw['qualifiers'] = sorted(kw['qualifiers'])
        return cls(**kw)

    def __str__(self):
        return '{}{}{}{}'.format(
            self.boundary_type,
            '_'.join((['ds'] if self.ds else []) +
                     ([self.clause_type] if self.clause_type else []) +
                     self.qualifiers),
            '.neg' if self.neg else ('.' + self.property if self.property else ''),
            ':{}'.format(self.function) if self.function else '')

#
# Referents:
# list of -/= separated annotations.
#


@dataclasses.dataclass
class Expression:
    form_gloss: str = None
    function: str = None
    morpheme_separator: str = None  # -, = may be leading or trailing!
    form_qualifiers: typing.List[str] = dataclasses.field(default_factory=list)
    function_qualifiers: typing.List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Predicate(Expression):
    def __str__(self):
        res = self.morpheme_separator or ''
        res += '_'.join(self.form_qualifiers + [self.form_gloss])
        if self.function:
            res += ':{}'.format('_'.join([self.function] + self.function_qualifiers))
        return res

    def describe(self, parser):
        res = 'form: '
        if (self.morpheme_separator, self.form_gloss) in parser.predicate_glosses:
            res += parser.predicate_glosses[(self.morpheme_separator, self.form_gloss)]
        else:
            res += parser.predicate_glosses[self.form_gloss]
        if self.form_qualifiers:
            res += ' ({})'.format(
                '; '.join(parser.form_gloss_specifiers[q] for q in  self.form_qualifiers))
        if self.function:
            res += '. function: {}'.format(parser.predicative_functions[self.function])
            if self.function_qualifiers:
                res += ' ({})'.format('; '.join(self.function_qualifiers))
        return res

    @classmethod
    def from_annotation(cls, annotation: str, parser=None) -> "Predicate":
        """
        1. check morpheme separator
        2. split off function, separated by :
        3. split by _. Rightmost is form, others are form_qualifiers
        """
        parser = parser or DEFAULT_PARSER
        kw = {}
        ann = annotation
        if any(ann.startswith(sep) for sep in parser.morpheme_separators):
            kw['morpheme_separator'], ann = ann[:1], ann[1:]
        ann, _, function = ann.partition(":")
        if function:
            function = function.split('_')
            if function[0] not in parser.predicative_functions:
                raise ValueError(annotation)
            kw['function'] = function[0]
            kw['function_qualifiers'] = function[1:]
        ann = ann.split("_")
        if ann:
            if ann[-1] not in parser.predicate_glosses:
                raise ValueError(annotation)
            kw['form_gloss'] = ann[-1]
            # FIXME: we need a fixed list of predicative function specifiers!?
            kw['form_qualifiers'] = ann[:-1]
            if not (ann[-1] in parser.predicate_glosses or tuple(ann[-2:]) in parser.predicate_glosses):
                raise ValueError(annotation)
            kw['form_gloss'] = ann.pop()
            if ann:
                if (ann[-1], kw['form_gloss']) in parser.predicate_glosses:
                    kw['form_qualifiers'] = [ann.pop()]
                for a in ann:
                    if a in parser.form_gloss_specifiers:
                        if 'form_qualifiers' in kw:
                            kw['form_qualifiers'].insert(0, a)
                        else:
                            kw['form_qualifiers'] = [a]
                    else:
                        raise ValueError(annotation)
        return cls(**kw)


@dataclasses.dataclass
class Referent(Expression):
    property: str = None
    subconstituent: str = None
    subconstituent_qualifiers: typing.List[str] = dataclasses.field(default_factory=list)

    def __str__(self):
        res = self.morpheme_separator or ''
        res += '_'.join(([self.subconstituent] if self.subconstituent else []) +
                        self.subconstituent_qualifiers +
                        self.form_qualifiers +
                        ([self.form_gloss] if self.form_gloss else []))
        if self.property:
            res += '.{}'.format(self.property)
        if self.function:
            res += ':{}'.format('_'.join([self.function] + self.function_qualifiers))
        return res

    @classmethod
    def from_annotation(cls, annotation: str, parser=None) -> "Referent":
        """
        1. check morpheme separator
        2. check subconstituent marker
        3. split off function, separated by :
        4. split off property, separated by .
        5. split by _. Rightmost is form, others are form_qualifiers
        """
        parser = parser or DEFAULT_PARSER
        kw = {}
        ann = annotation
        if any(ann.startswith(sep) for sep in parser.morpheme_separators):
            kw['morpheme_separator'], ann = ann[:1], ann[1:]
        if ann in parser.subconstituent_markers:
            kw['subconstituent'], ann = ann, ''
        elif any(ann.startswith(scm + '_') for scm in parser.subconstituent_markers):
            kw['subconstituent'], _, ann = ann.partition('_')
        if kw.get('subconstituent') and kw['subconstituent'] in parser.subconstituent_symbols:
            kw['subconstituent_qualifiers'] = []
            # Consume subconstituent_symbols from the left
            pattern = re.compile(
                r'(?P<sym>{})(_|$)'.format(
                    re_or(parser.subconstituent_symbols[kw['subconstituent']])))
            m = pattern.match(ann)
            while m:
                kw['subconstituent_qualifiers'].append(m.group('sym'))
                ann = ann[m.end():]
                m = pattern.match(ann)

        ann, _, function = ann.partition(":")
        if function:
            function = function.split('_')
            if not (function[0] in parser.syntactic_functions or function[0] in parser.predicative_functions):
                raise ValueError(annotation)
            kw['function'] = function[0]
            kw['function_qualifiers'] = function[1:]
        ann, _, property = ann.partition(".")
        if property:
            if property not in parser.referent_properties:
                raise ValueError(annotation)
            kw['property'] = property
        if ann:
            ann = ann.split("_")
            if not (ann[-1] in parser.form_glosses or tuple(ann[-2:]) in parser.form_glosses):
                raise ValueError(annotation)
            kw['form_gloss'] = ann.pop()
            if ann:
                if (ann[-1], kw['form_gloss']) in parser.form_glosses:
                    kw['form_qualifiers'] = [ann.pop()]
                for a in ann:
                    if a in parser.form_gloss_specifiers or a in parser.form_glosses:
                        if 'form_qualifiers' in kw:
                            kw['form_qualifiers'].insert(0, a)
                        else:
                            kw['form_qualifiers'] = [a]
                    else:
                        raise ValueError(annotation)
        return cls(**kw)
