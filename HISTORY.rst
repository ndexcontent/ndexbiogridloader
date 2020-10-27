=======
History
=======

0.3.0 (10-27-2020)
------------------

* Updated default ``--biogridversion`` version to ``4.2.191``

* All generated networks get networkx spring layout added by default

* Added tqdm progress bar support. Set ``--noprogressbar`` flag to disable

* Added --skipupload flag to skip the upload to NDEx step

* Added logic to retry failed upload of network to NDEx.
  ``--maxretries`` and ``--retry_sleep`` allow caller to control
  behavior

* Added ``--organismfile`` and ``--chemicalsfile`` to let caller override
  defaults

0.2.0 (2020-07-27)
------------------

* Updated default ``--biogridversion`` version to ``3.5.187``

* Modified organism_list file to include 3 strains of
  coronavirus (SARS-1, SARS-2 and MERS)

* Modified organism_style file to add an orange border
  to all viral protein nodes. This change affects all the
  both new and already existing viral organisms.

0.1.3 (2019-11-21)
------------------
Fixed a bug where networkType used to be a string, now it is a list of strings and we specify 'list_of_string'
type when setting networkType attribute with network.set_network_attribute("networkType", networkType, 'list_of_string').
This results in correct representation of networkType in CX model, for example:
{"n":"networkType","v":["interactome","ppi"],"d":"list_of_string"}.

0.1.2 (2019-10-25)
------------------
In organism_load_plan.json, changed types of edge columns
"Experimental System Type" and "Throughput" to be "list_of_string",
and "Score" to be "list_of_double".
This change resolves UD-761 Biogrid network can't be imported to Cytoscape.

0.1.1 (2019-08-23)
------------------
* First release on PyPI.
