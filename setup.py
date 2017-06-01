"""pyledgertools setup file"""

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='pyledgertools',
    version='0.1',
    description='Python based tools for ledger accounting.',
    long_description=readme(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: Public Domain',
        'Programming Language :: Python :: 3.5',
        'Topic :: Office/Business :: Financial :: Accounting',
    ],
    keywords='ledger-cli plaintextaccounting ofx',
    url='http://github.com/cgiacofei/pyledgertools',
    author='Chris Giacofei',
    author_email='c.giacofei@gmail.com',
    license='Public Domain',
    packages=['pyledgertools'],
    install_requires=[
        'nose',
        'ofxtools==custom',
        'PyYaml',
        'naiveBayesClassifier',
    ],
    dependency_links =
    ['https://github.com/csingley/ofxtools.git@6f8e1321ec5e452da06c583d254181e4eeb5099b#egg=ofxtools-custom'],
    include_package_data=True,
    zip_safe=False,
    entry_points = {
        'console_scripts': [
            'int-ofx=pyledgertools.cli:interactive',
            'auto-import=pyledgertools.cli:automatic',
            'journal-sort=pyledgertools.scripts.journal:sort_journal',
        ]
    },
    scripts = [
        'bin/accounts',
        'bin/find_transactions',
        'bin/find_files',
    ]
)
