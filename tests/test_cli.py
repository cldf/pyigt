import io

from pyigt.__main__ import main


def test_help(capsys):
    main([])
    out, _ = capsys.readouterr()
    assert 'usage' in out


def test_ls(metadata_path, capsys):
    main(['ls', str(metadata_path)])
    out, _ = capsys.readouterr()
    assert len(out.split('\n')) == 27

    main(['ls', str(metadata_path), 'Text_ID=2'])
    out, _ = capsys.readouterr()
    assert len(out.split('\n')) == 12


def test_ls_from_stdin(metadata_path, capsys, monkeypatch):
    monkeypatch.setattr(
        'sys.stdin',
        io.StringIO(
            'ID,Primary_Text,Analyzed_Word,Gloss,Translated_Text\n'
            '1,abc def,abc\tdef,A\tD,xyz'))
    main(['ls', '-'])
    out, _ = capsys.readouterr()
    assert len(out.split('\n')) == 6


def test_stats(metadata_path, capsys):
    main(['stats', str(metadata_path)])
    out, _ = capsys.readouterr()
    assert 'Text_ID' in out
