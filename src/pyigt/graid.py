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


class Gloss(typing.Protocol):  # pragma: no cover
    """
    Classes passed to GRAID as `other_glosses` must implement this protocol. I.e. implement a
    classmethod `from_annotation`, which returns an instance of the class if the annotation matches
    the pattern or `None` otherwise.
    """
    @classmethod
    def from_annotation(cls, annotation: str, parser: "GRAID" = None) -> typing.Optional["Gloss"]:
        """
        :return: `None` to signal that the annotation was not parsed, `Gloss` instance otherwise.
        """
        ...  # pragma: no cover

    def __str__(self) -> str:
        """
        The full gloss, re-assembled (and possibly normalized) or as passed to `from_annotation`.
        """
        ...

    def describe(self, parser: "GRAID" = None) -> typing.Dict[str, str]:
        ...


def update_symbols(symbols: SymbolDict,
                   d: SymbolDict,
                   attaches: typing.Union[typing.Literal['left'], typing.Literal['right']] = None):
    """
    Utility function to update GRAID symbol `dict`s.
    """
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
    """
    Concatenate strings in as regular expression pattern matching any of them.
    """
    return r'|'.join(re.escape(item) for item in items if isinstance(item, str))


class GRAID:
    """
    The GRAID 7.0 specification.
    """
    def __init__(self,
                 form_glosses: SymbolDict = None,
                 form_gloss_specifiers: SymbolDict = None,
                 referent_properties: SymbolDict = None,
                 syntactic_functions: SymbolDict = None,
                 syntactic_function_specifiers: SymbolDict = None,
                 predicate_glosses: SymbolDict = None,
                 clause_boundary_symbols: SymbolDict = None,
                 subconstituent_symbols: typing.Dict[str, typing.Tuple[str, list]] = None,
                 other_symbols: SymbolDict = None,
                 other_glosses: typing.Optional[typing.List[Gloss]] = None,
                 with_cross_index=False):
        """
        Almost all lists of symbols specified by the GRAID standard may be extended with new,
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
        self.syntactic_function_specifiers = syntactic_function_specifiers or {}
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
            '#nc': 'boundary, not considered',
            '##nc': 'boundary, not considered',
        }
        update_symbols(self.other_symbols, other_symbols)
        self.other_glosses = other_glosses or []
        if with_cross_index:
            self.other_glosses.append(CrossIndex)

    def iter_expressions(self, s) -> typing.Generator[str, None, None]:
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

    def __call__(self, gloss: str) \
            -> typing.List[typing.Union[Gloss, "Boundary", "Symbol", "Predicate", "Referent"]]:
        """
        Call a GRAID object to parse a full-word GRAID annotation.
        """
        return [self.parse_expression(exp) for exp in self.iter_expressions(gloss.strip())]

    def parse_expression(self, expression):
        for cls in self.other_glosses + [Symbol, Boundary, Predicate, Referent]:
            obj = cls.from_annotation(expression, self)
            if obj:
                return obj
        raise ValueError('Could not parse expression: {}'.format(expression))  # pragma: no cover

    def parse_function(self, function, predicate=False):
        kw = {}
        function = function.split('_')
        if predicate:
            if function[0] not in self.predicative_functions:
                raise ValueError(function)
        else:
            if not (function[0] in self.syntactic_functions or  # noqa: W504
                    function[0] in self.predicative_functions):
                raise ValueError(function)
        kw['function'] = function.pop(0)
        if function:
            if predicate:
                # GRAID doesn't support predicative function specifiers.
                raise ValueError(function)
            kw['function_qualifiers'] = []
            if (kw['function'], function[0]) in self.syntactic_functions:
                # Matches a specified function.
                kw['function_qualifiers'].append(function.pop(0))
            for fn in function:  # Check for generic function specifiers.
                if fn in self.syntactic_functions or fn in self.syntactic_function_specifiers:
                    kw['function_qualifiers'].append(fn)
                else:
                    raise ValueError(function)
        return kw


DEFAULT_PARSER = GRAID()


@dataclasses.dataclass
class Symbol:
    symbol: str
    morpheme_separator: str = None

    def __str__(self):
        return '{}{}'.format(self.morpheme_separator or '', self.symbol)

    def describe(self, parser: GRAID = None):
        parser = parser or GRAID()
        res = collections.OrderedDict()
        if self.morpheme_separator:
            res[self.morpheme_separator] = parser.morpheme_separators[self.morpheme_separator]
        res[self.symbol] = parser.other_symbols[self.symbol]
        return res

    @classmethod
    def from_annotation(cls, ann, parser) -> typing.Optional["Symbol"]:
        parser = parser or GRAID()
        kw = {}
        if any(ann.startswith(sep) for sep in parser.morpheme_separators):
            kw['morpheme_separator'], ann = ann[:1], ann[1:]
        if ann in parser.other_symbols:
            return cls(symbol=ann, **kw)


@dataclasses.dataclass
class Boundary:
    boundary_type: str
    clause_type: str = None
    ds: bool = False
    neg: bool = False
    property: str = None
    function: str = None
    function_qualifiers: typing.List[str] = dataclasses.field(default_factory=list)
    qualifiers: typing.List[str] = dataclasses.field(default_factory=list)

    def describe(self, parser: GRAID = None):
        parser = parser or GRAID()
        res = collections.OrderedDict()
        res[self.boundary_type] = parser.boundary_markers[self.boundary_type]
        if self.ds:
            res['ds'] = 'direct speech'
        if self.clause_type:
            res[self.clause_type] = parser.clause_types[self.clause_type]
        if self.neg:
            res['neg'] = 'negative polarity'
        if self.property:
            res[self.property] = parser.referent_properties[self.property]
        for q in self.qualifiers:
            res[q] = parser.clause_boundary_symbols[q]
        if self.function:
            res[self.function] = parser.predicative_functions.get(
                self.function, parser.syntactic_functions.get(self.function))
        for q in self.function_qualifiers:
            res[q] = parser.syntactic_function_specifiers[q]
        return res

    @classmethod
    def from_annotation(cls, annotation: str, parser=None) -> typing.Optional["Boundary"]:
        parser = parser or GRAID()
        for marker in parser.boundary_markers:
            if annotation.startswith(marker):
                break
        else:
            return

        parser = parser or DEFAULT_PARSER
        kw = {'qualifiers': [], 'boundary_type': marker, 'function_qualifiers': []}
        rem, _, function = annotation[len(kw["boundary_type"]):].partition(":")
        if function:
            kw.update(parser.parse_function(function))
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
        return '{}{}{}{}{}'.format(
            self.boundary_type,
            '_'.join((['ds'] if self.ds else []) +  # noqa: W504
                     ([self.clause_type] if self.clause_type else []) +  # noqa: W504
                     self.qualifiers),
            '.neg' if self.neg else ('.' + self.property if self.property else ''),
            ':{}'.format(self.function) if self.function else '',
            ''.join('_' + fq for fq in self.function_qualifiers),
        )


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

    def describe(self, parser: GRAID = None):
        parser = parser or GRAID()
        res = collections.OrderedDict()
        if (self.morpheme_separator, self.form_gloss) in parser.predicate_glosses:
            res[self.morpheme_separator + self.form_gloss] = parser.predicate_glosses[
                (self.morpheme_separator, self.form_gloss)]
        else:
            if self.morpheme_separator:
                res[self.morpheme_separator] = parser.morpheme_separators[self.morpheme_separator]
            res[self.form_gloss] = parser.predicate_glosses[self.form_gloss]

        if self.form_qualifiers:
            res['{}_{}'.format(self.form_qualifiers[0], self.form_gloss)] = (
                parser.predicate_glosses[(self.form_qualifiers[0], self.form_gloss)])

        if self.function:
            res[self.function] = parser.predicative_functions.get(
                self.function, parser.syntactic_functions.get(self.function))
        assert not self.function_qualifiers
        return res

    @classmethod
    def from_annotation(cls, annotation: str, parser=None) -> typing.Optional["Predicate"]:
        """
        1. check morpheme separator
        2. split off function, separated by :
        3. split by _. Rightmost is form, others are form_qualifiers
        """
        parser = parser or DEFAULT_PARSER
        kw = {}
        ann = annotation

        if ann in parser.syntactic_functions or ann in parser.predicative_functions:
            ann = ':' + ann

        ann, _, function = ann.partition(':')
        if any(ann.startswith(sep) for sep in parser.morpheme_separators):
            kw['morpheme_separator'], ann = ann[:1], ann[1:]
        ann = ann.split('_')
        if ann[0] in parser.subconstituent_markers:
            return
        if not (ann[-1] in parser.predicate_glosses or tuple(ann[-2:]) in parser.predicate_glosses):
            # Don't raise an error, because this may still be parsed as valid Referent!
            return

        # Now we know it's supposed to be a predicate. So parsing problems mean raising ValueError.
        if function:
            kw.update(parser.parse_function(function, predicate=True))
        if ann:
            kw['form_gloss'] = ann.pop()
            kw['form_qualifiers'] = []
            if ann:
                if (ann[-1], kw['form_gloss']) in parser.predicate_glosses:
                    kw['form_qualifiers'].append(ann.pop())
            if ann:  # GRAID does not support further specified predicate glosses.
                raise ValueError(annotation)
        return cls(**kw)


@dataclasses.dataclass
class Referent(Expression):
    property: str = None
    subconstituent: str = None
    subconstituent_qualifiers: typing.List[str] = dataclasses.field(default_factory=list)

    def __str__(self):
        res = self.morpheme_separator or ''
        res += '_'.join(([self.subconstituent] if self.subconstituent else []) +  # noqa: W504
                        self.subconstituent_qualifiers +  # noqa: W504
                        self.form_qualifiers +  # noqa: W504
                        ([self.form_gloss] if self.form_gloss else []))
        if self.property:
            res += '.{}'.format(self.property)
        if self.function:
            res += ':{}'.format('_'.join([self.function] + self.function_qualifiers))
        return res

    def describe(self, parser: GRAID = None):
        parser = parser or GRAID()
        res = collections.OrderedDict()
        if (self.morpheme_separator, self.form_gloss) in parser.form_glosses:
            res[self.morpheme_separator + self.form_gloss] = parser.form_glosses[
                (self.morpheme_separator, self.form_gloss)]
        else:
            if self.morpheme_separator:
                res[self.morpheme_separator] = parser.morpheme_separators[self.morpheme_separator]

        if self.subconstituent:
            res[self.subconstituent] = parser.subconstituent_markers[self.subconstituent]
        for q in self.subconstituent_qualifiers:
            res[q] = parser.subconstituent_symbols[self.subconstituent][q]

        if self.form_gloss:
            res[self.form_gloss] = parser.form_glosses[self.form_gloss]

        for i, q in enumerate(reversed(self.form_qualifiers)):
            if i == 0:
                if (q, self.form_gloss) in parser.form_glosses:
                    res['{}_{}'.format(q, self.form_gloss)] = (
                        parser.form_glosses[(q, self.form_gloss)])
                else:
                    res[q] = parser.form_glosses.get(q, parser.form_gloss_specifiers.get(q))
            else:
                res[q] = parser.form_glosses.get(q, parser.form_gloss_specifiers.get(q))

        start = 0
        if self.function:
            if (self.function_qualifiers and  # noqa: W504
                    (self.function, self.function_qualifiers[0]) in parser.syntactic_functions):
                res['{}_{}'.format(self.function, self.function_qualifiers[0])] = (
                    parser.syntactic_functions)[(self.function, self.function_qualifiers[0])]
                start = 1
            else:
                res[self.function] = parser.predicative_functions.get(
                    self.function, parser.syntactic_functions.get(self.function))
        for q in self.function_qualifiers[start:]:
            res[q] = parser.syntactic_function_specifiers[q]
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
        if ann in parser.syntactic_functions or ann in parser.predicative_functions:
            ann = ':' + ann
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
            kw.update(parser.parse_function(function))
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
            kw['form_qualifiers'] = []
            if ann:
                if (ann[-1], kw['form_gloss']) in parser.form_glosses:
                    kw['form_qualifiers'].append(ann.pop())
                for a in ann:
                    if a in parser.form_gloss_specifiers or a in parser.form_glosses:
                        kw['form_qualifiers'].insert(0, a)
                    else:
                        raise ValueError(annotation)
        return cls(**kw)


@dataclasses.dataclass
class CrossIndex:
    """
    Several Multi-CAST corpora include annotations of "cross-indeces". The GRAID parser can be
    conditioned to recognize such indeces by passing `with_cross_index=True` on instantiation.
    """
    referent_property: str
    function: str
    subconstituent_marker: str = None
    morpheme_separator: str = None

    def __str__(self):
        return '{}{}pro_{}_{}'.format(
            self.morpheme_separator or '',
            self.subconstituent_marker + '_' if self.subconstituent_marker else '',
            self.referent_property,
            self.function,
        )

    def describe(self, parser: GRAID = None) -> typing.Dict[str, str]:
        parser = parser or GRAID()
        return {'symbol': str(self)}

    @classmethod
    def from_annotation(cls, ann, parser: GRAID = None) -> typing.Optional["CrossIndex"]:
        parser = parser or GRAID()
        kw = {}
        if any(ann.startswith(sep) for sep in parser.morpheme_separators):
            kw['morpheme_separator'], ann = ann[:1], ann[1:]
        for scm in parser.subconstituent_markers:
            if ann.startswith(scm + '_'):
                kw['subconstituent_marker'], ann = scm, ann[len(scm) + 1:]
        m = re.fullmatch(
            r'pro_(?P<rp>{})_(?P<f>{})'.format(
                re_or(parser.referent_properties), re_or(parser.syntactic_functions)),
            ann)
        if m:
            kw['referent_property'], kw['function'] = m.group('rp'), m.group('f')
            return cls(**kw)
