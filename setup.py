"""Setup 'djtools' package.
"""
from pathlib import Path
from setuptools import setup


with open('README.md', encoding='utf-8') as _file:
    LONG_DESCRIPTION = _file.read()

REQUIREMENTS = [
    "asyncpraw==7.6.1",
    "awscli==1.27.45",
    "beautifulsoup4==4.11.1",
    "fuzzywuzzy==0.18.0",
    "lxml==4.9.2",
    "pydantic==1.9.1",
    "pyperclip==1.8.2",
    "PyYAML==5.4.1",
    "requests==2.28.0",
    "setuptools==58.1.0",
    "spotipy==2.21.0",
    "tqdm==4.64.0",
    "youtube-dl==2021.12.17",
]

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: Other Audience',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Natural Language :: English',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Topic :: Multimedia :: Sound/Audio',
    'Topic :: Other/Nonlisted Topic'
]

EXTRAS = {
        'levenshtein': ['python-Levenshtein==0.12.2']
}

version_path = Path(__file__).parent / "djtools" / "version.py"
with open(version_path, mode="r", encoding="utf-8") as _file:
    VERSION = _file.read().split("=")[-1].strip().replace('"', "")

setup(
    name='dj_beatcloud',
    version=VERSION,
    description='DJ Tools is a library for managing a collection of music.',
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url='https://github.com/a-rich/DJ-tools',
    author='Alex Richards',
    author_email='alex.richards006@gmail.com',
    packages=[
        "djtools",
        "djtools.configs",
        "djtools.collection",
        "djtools.spotify",
        "djtools.sync",
        "djtools.utils",
    ],
    classifiers=CLASSIFIERS,
    install_requires=REQUIREMENTS,
    extras_require=EXTRAS,
    python_requires=">=3.6",
    include_package_data=True,
    keywords='DJ Rekordbox spotify reddit aws s3',
    entry_points={
        'console_scripts': ['djtools=djtools:main']
    },
)
