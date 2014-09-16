import os, subprocess
from distutils.core import setup
from distutils.command.install import install



setup(
    name='XlinkAnalyzer',
    version='0.99dev',
    author='Jan Kosinski',
    author_email='jan.kosinski@embl.de',
    packages=['xlinkanalyzer'
              ],
    url='none',
    license='LICENSE.txt',
    description='Cross-linking visualization and analysis in UCSF Chimera.',
    long_description=open('README').read(),
)
