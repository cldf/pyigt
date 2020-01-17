from pyigt.__main__ import main


def test_ls(metadata_path, capsys):
    main(['ls', str(metadata_path)])
    out, _ = capsys.readouterr()
    assert len(out.split('\n')) == 21

    main(['ls', str(metadata_path), '-c', 'Text_ID', '-m', '2'])
    out, _ = capsys.readouterr()
    assert len(out.split('\n')) == 9