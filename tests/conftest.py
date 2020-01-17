import pathlib

import pytest

from pycldf import Dataset


@pytest.fixture
def metadata_path():
    return pathlib.Path(__file__).parent / 'fixtures' / 'cldf-metadata.json'


@pytest.fixture
def dataset(metadata_path):
    return Dataset.from_metadata(metadata_path)
