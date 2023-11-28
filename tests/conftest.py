import pathlib

import pytest

from pycldf import Dataset


@pytest.fixture
def fixtures():
    return pathlib.Path(__file__).parent / 'fixtures'


@pytest.fixture
def metadata_path(fixtures):
    return fixtures / 'cldf-metadata.json'


@pytest.fixture
def dataset(metadata_path):
    return Dataset.from_metadata(metadata_path)


@pytest.fixture
def multilingual_dataset(fixtures):
    return Dataset.from_metadata(fixtures / 'multilingual' / 'cldf-metadata.json')


@pytest.fixture(scope='session')
def lgr_examples():
    from pyigt import Example
    cldf = Dataset.from_metadata(
        pathlib.Path(__file__).parent / 'fixtures' / 'lgr' / 'cldf' / 'Generic-metadata.json')
    return cldf.objects('ExampleTable', cls=Example)


def pytest_generate_tests(metafunc):
    from pyigt import Example

    cldf = Dataset.from_metadata(
        pathlib.Path(__file__).parent / 'fixtures' / 'lgr' / 'cldf' / 'Generic-metadata.json')
    if "lgr_example" in metafunc.fixturenames:
        metafunc.parametrize("lgr_example", cldf.objects('ExampleTable', cls=Example))
