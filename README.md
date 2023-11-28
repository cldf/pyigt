# pyigt: Handling interlinear glossed text with Python

[![Build Status](https://github.com/cldf/pyigt/workflows/tests/badge.svg)](https://github.com/cldf/pyigt/actions?query=workflow%3Atests)
[![PyPI](https://img.shields.io/pypi/v/pyigt.svg)](https://pypi.org/project/pyigt)
[![Documentation Status](https://readthedocs.org/projects/pyigt/badge/?version=latest)](https://pyigt.readthedocs.io/en/latest/?badge=latest)

This library provides easy access to **I**nterlinear **G**lossed **T**ext (IGT) according
to the [Leipzig Glossing Rules](https://www.eva.mpg.de/lingua/resources/glossing-rules.php), stored as 
[CLDF examples](https://github.com/cldf/cldf/tree/master/components/examples).


## Installation

Installing `pyigt` via pip

```shell
pip install pyigt
```
will install the Python package along with a [command line interface `igt`](#cli).

Note: The methods `Corpus.get_wordlist` and `Corpus.get_profile`, to extract a wordlist and an orthography profile
from a corpus, require the `lingpy` package. To make sure it is installed, install `pyigt` as
```shell
pip install pyigt[lingpy]
```

## CLI

```shell script
$ igt -h
usage: igt [-h] [--log-level LOG_LEVEL] COMMAND ...

optional arguments:
  -h, --help            show this help message and exit
  --log-level LOG_LEVEL
                        log level [ERROR|WARN|INFO|DEBUG] (default: 20)

available commands:
  Run "COMAMND -h" to get help for a specific command.

  COMMAND
    ls                  List IGTs in a CLDF dataset
    stats               Describe the IGTs in a CLDF dataset

```

The `igt ls` command allows inspecting IGTs from the commandline, formatted using the
four standard lines described in the Leipzig Glossing Rules, where analyzed text and
glosses are aligned, e.g.
```shell script
$ igt ls tests/fixtures/examples.csv 
Example 1:
zəple: ȵike: peji qeʴlotʂuʁɑ,
zəp-le:       ȵi-ke:       pe-ji       qeʴlotʂu-ʁɑ,
earth-DEF:CL  WH-INDEF:CL  become-CSM  in.the.past-LOC

...

Example 5:
zuɑməɸu oʐgutɑ ipiχuɑȵi,
zuɑmə-ɸu      o-ʐgu-tɑ    i-pi-χuɑ-ȵi,
cypress-tree  one-CL-LOC  DIR-hide-because-ADV

IGT corpus at tests/fixtures/examples.csv
```

`igt ls` can be chained with other commandline tools such as commands from the 
[csvkit](https://csvkit.readthedocs.io/en/latest/) package for filtering:
```shell script
$ csvgrep -c Primary_Text -m"ȵi"  tests/fixtures/examples.csv | csvgrep -c Gloss -m"ADV" |  igt ls -
Example 5:
zuɑməɸu oʐgutɑ ipiχuɑȵi,
zuɑmə-ɸu      o-ʐgu-tɑ    i-pi-χuɑ-ȵi,
cypress-tree  one-CL-LOC  DIR-hide-because-ADV

```


## Python API

The Python API is documented in detail at [readthedocs](https://pyigt.readthedocs.io/en/latest/).
Below is a quick overview.

You can read all IGT examples provided with a CLDF dataset

```python
>>> from pyigt import Corpus
>>> corpus = Corpus.from_path('tests/fixtures/cldf-metadata.json')
>>> len(corpus)
5
>>> for igt in corpus:
...     print(igt)
...     break
... 
zəple: ȵike: peji qeʴlotʂuʁɑ,
zəp-le:       ȵi-ke:       pe-ji       qeʴlotʂu-ʁɑ,
earth-DEF:CL  WH-INDEF:CL  become-CSM  in.the.past-LOC
```

or instantiate individual IGT examples, e.g. to check for validity:
```python
>>> from pyigt import IGT
>>> ex = IGT(phrase="palasi=lu", gloss="priest-and")
>>> ex.check(strict=True, verbose=True)
palasi=lu
priest-and
...
ValueError: Rule 2 violated: Number of morphemes does not match number of morpheme glosses!
```
or to expand known gloss abbreviations:
```python
>>> ex = IGT(phrase="Gila abur-u-n ferma hamišaluǧ güǧüna amuq’-da-č.",
...          gloss="now they-OBL-GEN farm forever behind stay-FUT-NEG", 
...          translation="Now their farm will not stay behind forever.")
>>> ex.pprint()
Gila aburun ferma hamišaluǧ güǧüna amuq’dač.
Gila    abur-u-n      ferma    hamišaluǧ    güǧüna    amuq’-da-č.
now     they-OBL-GEN  farm     forever      behind    stay-FUT-NEG
‘Now their farm will not stay behind forever.’
  OBL = oblique
  GEN = genitive
  FUT = future
  NEG = negation, negative
```

And you can go deeper, parsing morphemes and glosses according to the LGR 
(see module [pyigt.lgrmorphemes](src/pyigt/lgrmorphemes.py)):

```python
>>> igt = IGT(phrase="zəp-le: ȵi-ke: pe-ji qeʴlotʂu-ʁɑ,", gloss="earth-DEF:CL WH-INDEF:CL become-CSM in.the.past-LOC")
>>> igt.conformance
<LGRConformance.MORPHEME_ALIGNED: 2>
>>> igt[1, 1].gloss
<Morpheme "INDEF:CL">
>>> igt[1, 1].gloss.elements
[<GlossElement "INDEF">, <GlossElementAfterColon "CL">]
>>> igt[1, 1].morpheme
<Morpheme "ke:">
>>> print(igt[1, 1].morpheme)
ke:
```


## See also

- [interlineaR](https://cran.r-project.org/web/packages/interlineaR/index.html) - an R package with similar functionality, but support for more input formats.
