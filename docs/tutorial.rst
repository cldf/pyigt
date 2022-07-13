Tutorial
========

The `pyigt` package provides an API to access
`interlinear glossed text <https://en.wikipedia.org/wiki/Interlinear_gloss>`_
from Python code.


Glossed phrases
---------------

In the simplest case, interlinear glossed text is provided as phrase-chunked pairs of object language and
gloss lines - an instance of :class:`pyigt.IGT`:

.. code-block:: python

    >>> from pyigt import IGT
    >>> igt = IGT(phrase="ni-c-chihui-lia in no-piltzin ce calli", gloss="1SG.SUBJ-3SG.OBJ-mach-APPL DET 1SG.POSS-Sohn ein Haus")
    >>> print(igt)
    nicchihuilia in nopiltzin ce calli
    ni-c-chihui-lia             in    no-piltzin     ce    calli
    1SG.SUBJ-3SG.OBJ-mach-APPL  DET   1SG.POSS-Sohn  ein   Haus

Such a chunk consists of aligned, glossed words (conventionally separated by whitespace):

.. code-block:: python

    >>> for word in igt:
    ...     print(word)
    ...
    <GlossedWord word=ni-c-chihui-lia gloss=1SG.SUBJ-3SG.OBJ-mach-APPL>
    <GlossedWord word=in gloss=DET>
    <GlossedWord word=no-piltzin gloss=1SG.POSS-Sohn>
    <GlossedWord word=ce gloss=ein>
    <GlossedWord word=calli gloss=Haus>


Zooming in: Morphemes and gloss elements
----------------------------------------

The words (and glosses) are segmented into glossed morphemes (:class:`~pyigt.lgrmorphemes.GlossedMorpheme`)

.. code-block:: python

    >>> igt[0, 0:]
    [<GlossedMorpheme morpheme=ni gloss=1SG.SUBJ>, <GlossedMorpheme morpheme=c gloss=3SG.OBJ>, <GlossedMorpheme morpheme=chihui gloss=mach>, <GlossedMorpheme morpheme=lia gloss=APPL>]
    >>> igt[0, 0].grammatical_concepts
    ['1SG.SUBJ']
    >>> igt[2, 1].lexical_concepts
    ['Sohn']
    >>> igt[0, 0].gloss.elements
    [<GlossElement "1SG">, <GlossElement "SUBJ">]


Zooming out: Collections of IGT - a corpus
------------------------------------------

Collections of IGTs form a :class:`pyigt.Corpus`

.. code-block:: python

    >>> from pyigt import Corpus
    >>> c = Corpus([igt, igt])
    >>> c[0, 0, 0]
    <GlossedMorpheme morpheme=ni gloss=1SG.SUBJ>
    >>> c.get_concepts('grammar')['APPL'][0].refs
    [(0, 0, 3), (1, 0, 3)]
