"""Setup 'djtools' package.
"""
from setuptools import find_packages, setup


with open('README.md', encoding='utf-8') as _file:
    LONG_DESCRIPTION = _file.read()

REQUIREMENTS = [
    "awscli==1.22.27",
    "beautifulsoup4==4.10.0",
    "botocore==1.23.27",
    "bs4==0.0.1",
    "certifi==2021.10.8",
    "charset-normalizer==2.0.9",
    "colorama==0.4.3",
    "coverage==5.5",
    "deprecation==2.1.0",
    "docutils==0.15.2",
    "eyed3==0.9.6",
    "filetype==1.0.9",
    "fuzzywuzzy==0.18.0",
    "idna==3.3",
    "jmespath==0.10.0",
    "packaging==21.3",
    "praw==7.5.0",
    "prawcore==2.3.0",
    "pyasn1==0.4.8",
    "pyparsing==3.0.6",
    "python-dateutil==2.8.2",
    "python-Levenshtein==0.12.2",
    "PyYAML==5.4.1",
    "requests==2.27.0",
    "rsa==4.7.2",
    "s3transfer==0.5.0",
    "six==1.16.0",
    "soupsieve==2.3.1",
    "spotipy==2.19.0",
    "toml==0.10.2",
    "tqdm==4.62.3",
    "update-checker==0.18.0",
    "urllib3==1.26.7",
    "websocket-client==1.2.3",
    "youtube-dl==2021.12.17"
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

setup(
    name='dj_beatcloud',
    version='2.0.1',
    description='DJ Tools is a library for managing a collection of MP3 ' \
                'and Rekordbox XML files.',
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url='https://github.com/a-rich/DJ-tools',
    author='Alex Richards',
    author_email='alex.richards006@gmail.com',
    license='GNU GPLv3',
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=CLASSIFIERS,
    install_requires=REQUIREMENTS,
    python_requires=">=3.6",
    include_package_data=True,
    keywords='MP3 Rekordbox XML spotify reddit aws s3',
    entry_points={
        'console_scripts': ['djtools=djtools:dj_tools.main']
    }
)
