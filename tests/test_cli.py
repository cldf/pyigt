import pytest

from pyigt.__main__ import main


def test_help(capsys):
    main([])
    out, _ = capsys.readouterr()
    assert 'usage' in out


def test_ls(metadata_path, capsys):
    main(['ls', str(metadata_path)])
    out, _ = capsys.readouterr()
    assert len(out.split('\n')) == 26

    main(['ls', str(metadata_path), '-c', 'Text_ID', '-m', '2'])
    out, _ = capsys.readouterr()
    assert len(out.split('\n')) == 11


def test_stats(metadata_path, capsys):
    main(['stats', str(metadata_path)])
    out, _ = capsys.readouterr()
    assert 'Text_ID' in out
