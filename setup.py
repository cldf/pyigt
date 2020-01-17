#import distribute_setup
#distribute_setup.use_setuptools()

from setuptools import setup, find_packages,Extension
import codecs
# setup package name etc as a default
pkgname = 'pyigt'


setup(
        name=pkgname,
        description="A Python library for handling inter-linear-glossed text.",
        version='0.1.0',
        packages=find_packages(where='src'),
        package_dir={'': 'src'},
        zip_safe=False,
        license="GPL",
        include_package_data=True,
        install_requires=[
            'csvw',
            'clldutils',
            'lingpy>=2.6.5',
            'cldfcatalog',
            'pyclts',
            'pyconcepticon',
            'segments>=2.0.0',
            ],
        url='https://github.com/lingpy/pyigt',
        long_description=codecs.open('README.md', 'r', 'utf-8').read(),
        long_description_content_type='text/markdown',
        author='Johann-Mattis List',
        author_email='list@shh.mpg.de',
        keywords='Chinese linguistics, historical linguistics, computer-assisted language comparison'
        )
