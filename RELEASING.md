
Releasing pyigt
===============

- Do platform test via tox:
```shell
tox -r
```

- Make sure statement coverage >= 99%
- Make sure flake8 passes:
```shell
flake8 src
```

- Make sure docs can be created:
```shell
cd docs
make clean html
cd ..
```

- Update the version number, by removing the trailing `.dev0` in:
  - `setup.cfg`
  - `src/pyigt/__init__.py`
  - `docs/conf.py`
  - edit `CHANGELOG.md`

- Create the release commit:
```shell
git commit -a -m "release <VERSION>"
```

- Create a release tag:
```
git tag -a v<VERSION> -m"<VERSION> release"
```

- Release to PyPI:
```shell
rm dist/*
python -m build -n
twine upload dist/*
```

- Push to github:
```shell
git push origin
git push --tags
```

- Change version for the next release cycle, i.e. incrementing and adding .dev0
  - `setup.cfg`
  - `src/pyigt/__init__.py`
  - `docs/conf.py`

- Commit/push the version change:
```shell
git commit -a -m "bump version for development"
git push origin
```
