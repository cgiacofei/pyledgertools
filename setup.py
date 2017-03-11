"""pyledgertools setup file"""

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='pyledgertools',
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
        'ofxtools',
        'PyYaml',
      ],
      include_package_data=True,
      zip_safe=False)
