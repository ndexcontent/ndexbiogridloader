===========================
NDEx BioGRID Content Loader
===========================


.. image:: https://img.shields.io/pypi/v/ndexbiogridloader.svg
        :target: https://pypi.python.org/pypi/ndexbiogridloader

.. image:: https://img.shields.io/travis/ndexcontent/ndexbiogridloader.svg
        :target: https://travis-ci.org/ndexcontent/ndexbiogridloader

.. image:: https://coveralls.io/repos/github/ndexcontent/ndexbiogridloader/badge.svg?branch=master
        :target: https://coveralls.io/github/ndexcontent/ndexbiogridloader?branch=master

.. image:: https://readthedocs.org/projects/ndexbiogridloader/badge/?version=latest
        :target: https://ndexbiogridloader.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


Python application for loading BioGRID data into `NDEx <http://ndexbio.org>`_.

This tool downloads and unpacks the `BioGRID <https://thebiogrid.org/>`_ files below

    `BIOGRID-ORGANISM-3.5.187.tab2.zip <https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive/BIOGRID-3.5.187/BIOGRID-ORGANISM-3.5.87.tab2.zip>`_

    `BIOGRID-CHEMICALS-3.5.187.chemtab.zip <https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive/BIOGRID-3.5.187/BIOGRID-CHEMICALS-3.5.187.chemtab.zip>`_

**NOTE:** ``ndexloadbiogrid.py`` script ``--biogridversion`` parameter dictates version (``3.5.187`` above)





Dependencies
------------

* `ndex2 <https://pypi.org/project/ndex2>`_
* `ndexutil <https://pypi.org/project/ndexutil>`_

Compatibility
-------------

* Python 3.3+

Installation
------------

.. code-block::

   git clone https://github.com/ndexcontent/ndexbiogridloader
   cd ndexbiogridloader
   make dist
   pip install dist/ndexloadbiogrid*whl


Run **make** command with no arguments to see other build/deploy options including creation of Docker image

.. code-block::

   make

Output:

.. code-block::

   clean                remove all build, test, coverage and Python artifacts
   clean-build          remove build artifacts
   clean-pyc            remove Python file artifacts
   clean-test           remove test and coverage artifacts
   lint                 check style with flake8
   test                 run tests quickly with the default Python
   test-all             run tests on every Python version with tox
   coverage             check code coverage quickly with the default Python
   docs                 generate Sphinx HTML documentation, including API docs
   servedocs            compile the docs watching for changes
   testrelease          package and upload a TEST release
   release              package and upload a release
   dist                 builds source and wheel package
   install              install the package to the active Python's site-packages
   dockerbuild          build docker image and store in local repository
   dockerpush           push image to dockerhub


Configuration
-------------

The **ndexloadbiogrid.py** requires a configuration file in the following format be created.
The default path for this configuration is :code:`~/.ndexutils.conf` but can be overridden with
:code:`--conf` flag.

**Format of configuration file:**

.. code-block::

    [<value in --profile (default ndexbiogridloader)>]

    user = <NDEx username>
    password = <NDEx password>
    server = <NDEx server(omit http) ie public.ndexbio.org>

**Example of default configuration file:**

.. code-block::

    [ndexbiogridloader]
    user = joe123
    password = somepassword123
    server = dev.ndexbio.org



Usage
-----

For information invoke :code:`ndexloadbiogrid.py -h`

The command shown below will download the default version of BioGRID files (3.5.178) to the working
directory :code:`biogrid_data`, will generate CX networks in this directory, and then upload these networks
to default account specified in :code:`[ndexbiogridloader]` section of default configuration file:

.. code-block::

   ndexloadbiogrid.py biogrid_data




Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

