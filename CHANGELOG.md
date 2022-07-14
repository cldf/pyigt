# Changes
  

## [Unreleased]


## [2.0.0] - 2022-07-14

- Unified treatment of gloss elements (according to LGR) in `IGT` and `Corpus` objects.
- Docs on rtd

### Backward Incompatibilities

`CorpusSpec` has been removed, and consequently `Corpus` and `IGT` do not
accept a `spec` keyword argument anymore.
Removal of `CorpusSpec` may also lead to slightly different output from
the `write_*` methods of `Corpus`.

