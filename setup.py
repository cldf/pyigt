from setuptools import setup, find_packages
import codecs


setup(
    name='pyigt',
    description="A Python library for handling inter-linear-glossed text.",
    version='1.3.0',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    zip_safe=False,
    license="GPL",
    include_package_data=True,
    install_requires=[
        'attrs',
        'csvw',
        'clldutils',
        'pycldf',
        'lingpy>=2.6.5',
        'segments>=2.0.0',
        'tabulate',
    ],
    url='https://github.com/cldf/pyigt',
    long_description=codecs.open('README.md', 'r', 'utf-8').read(),
    long_description_content_type='text/markdown',
    author='Johann-Mattis List and Robert Forkel',
    author_email='mattis_list@eva.mpg.de',
    keywords='Chinese linguistics, historical linguistics, computer-assisted language comparison',
    extras_require={
        'dev': ['flake8', 'wheel', 'twine'],
        'test': [
            'pytest>=5',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
        ],
    },
    entry_points={
        'console_scripts': [
            'igt=pyigt.__main__:main',
        ]
    },
)
