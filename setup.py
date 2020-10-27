#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
import os
import re
from setuptools import setup, find_packages


with open(os.path.join('ndexbiogridloader', '__init__.py')) as ver_file:
    for line in ver_file:
        if line.startswith('__version__'):
            version=re.sub("'", "", line[line.index("'"):])

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['ndex2>=3.1.0a1,<=4.0.0',
                'ndexutil>=0.1.0a3,<=1.0.0',
                'requests',
                'pandas',
                'networkx',
                'scipy',
                'tqdm']

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Vladimir Rynkov",
    author_email='vrynkov@yahoo.edu',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Loads BioGRID data into NDEx",
    install_requires=requirements,
    license="BSD license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='ndexbiogridloader',
    name='ndexbiogridloader',
    packages=find_packages(include=['ndexbiogridloader']),
    scripts=[ 'ndexbiogridloader/ndexloadbiogrid.py'],
    package_data={'ndexbiogridloader':
      ['chem_load_plan.json', 'organism_load_plan.json', 'chemical_style.cx', 'organism_style.cx',
       'chemicals_list.txt', 'organism_list.txt']},
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/ndexcontent/ndexbiogridloader',
    version=version,
    zip_safe=False,
)
