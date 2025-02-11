# Changes

## unreleased

- Support parsing GRAID annotations.

  
## [2.2.0] - 2025-01-15

- Support Multi-CAST style IGts, i.e. prefixes or suffixes glossed as words, thus "words" starting
  or ending with a morpheme separator.
- Support for Python 3.13.


## [2.1.0] - 2023-11-28

- Dropped support for Python 3.7.
- Added support for Python 3.11 and 3.12.
- Use the LGR CLDF dataset as conformance test suite.
- Added a `pycldf.orm.Example` subclass to easily instantiate `IGT` objects from CLDF data.


## [2.0.0] - 2022-07-14

- Unified treatment of gloss elements (according to LGR) in `IGT` and `Corpus` objects.
- Docs on rtd

### Backward Incompatibilities

`CorpusSpec` has been removed, and consequently `Corpus` and `IGT` do not
accept a `spec` keyword argument anymore.
Removal of `CorpusSpec` may also lead to slightly different output from
the `write_*` methods of `Corpus`.

