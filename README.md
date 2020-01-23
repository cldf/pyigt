# pyigt: Handling interlinear glossed text with Python

[![Build Status](https://travis-ci.org/cldf/pyigt.svg?branch=master)](https://travis-ci.org/cldf/pyigt)
[![codecov](https://codecov.io/gh/cldf/pyigt/branch/master/graph/badge.svg)](https://codecov.io/gh/cldf/pyigt)
[![PyPI](https://img.shields.io/pypi/v/pyigt.svg)](https://pypi.org/project/pyigt)

This library provides easy access to **I**nterlinear **G**lossed **T**ext (IGT) according
to the [Leipzig Glossing Rules](https://www.eva.mpg.de/lingua/resources/glossing-rules.php), stored as [CLDF examples](https://github.com/cldf/cldf/tree/master/components/examples).


## Installation

Installing `pyigt` via pip

```shell script
pip install pyigt
```
will install the Python package along with a command line interface `igt`.

## Usage

### CLI

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


### Python API

```python
>>> from pyigt import Corpus
>>> corpus = Corpus.from_path('tests/fixtures/cldf-metadata.json')
>>> len(corpus)
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


## See also

- [interlineaR](https://cran.r-project.org/web/packages/interlineaR/index.html) - an R package with similar functionality, but support for more input formats.
