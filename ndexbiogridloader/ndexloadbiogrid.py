#! /usr/bin/env python

import argparse
import sys
import logging
import time
from logging import config
from ndexutil.config import NDExUtilConfig
import ndexbiogridloader
import requests
import os
import zipfile
import ndex2
from ndex2.client import Ndex2
import networkx as nx
from tqdm import tqdm


logger = logging.getLogger(__name__)


TSV2NICECXMODULE = 'ndexutil.tsv.tsv2nicecx2'

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"


import json
import pandas as pd
import ndexutil.tsv.tsv2nicecx2 as t2n


class Formatter(argparse.ArgumentDefaultsHelpFormatter,
                argparse.RawDescriptionHelpFormatter):
    pass


ORGANISM_STYLE = 'organism_style.cx'
CHEMICAL_STYLE = 'chemical_style.cx'


ORGANISMLISTFILE = 'organism_list.txt'
"""
Name of file containing list of networks to be downloaded
stored within this package
"""

CHEMICALSLISTFILE = 'chemicals_list.txt'
"""
Name of file containing list of networks to be downloaded
stored within this package
"""

TESTSDIR = 'tests'
"""
Name of the test directoryl; used in test_ndexloadtcga.py module
"""

DATADIR = 'biogrid_files'
"""
Name of directory where biogrid archived files will be downloaded to and processed
"""

ORGANISM_LOAD_PLAN = 'organism_load_plan.json'
"""
Name of file containing json load plan
for biogrid protein-protein interactions
"""

CHEM_LOAD_PLAN = 'chem_load_plan.json'
"""
Name of file containing json load plan
for biogrid protein-chemical interactions
"""


def get_package_dir():
    """
    Gets directory where package is installed
    :return:
    """
    return os.path.dirname(ndexbiogridloader.__file__)


def get_organism_style():
    """
    Gets the style stored with this package

    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), ORGANISM_STYLE)


def get_chemical_style():
    """
    Gets the style stored with this package

    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), CHEMICAL_STYLE)


def get_organism_load_plan():
    """
    Gets the load plan stored with this package
    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), ORGANISM_LOAD_PLAN)


def get_chemical_load_plan():
    """
    Gets the load plan stored with this package
    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), CHEM_LOAD_PLAN)


def get_organismfile():
    """
    Gets the networks list stored with this package
    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), ORGANISMLISTFILE)


def get_chemicalsfile():
    """
    Gets the networks lsist stored with this package
    :return: path to file
    :rtype: string
    """
    return os.path.join(get_package_dir(), CHEMICALSLISTFILE)


def _parse_arguments(desc, args):
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=Formatter)
    parser.add_argument('datadir', help='Directory where BioGRID data downloaded to and processed from')

    parser.add_argument('--profile', help='Profile in configuration '
                                          'file to use to load '
                                          'NDEx credentials which means'
                                          'configuration under [XXX] will be'
                                          'used '
                                          '(default '
                                          'ndexbiogridloader)',
                        default='ndexbiogridloader')
    parser.add_argument('--logconf', default=None,
                        help='Path to python logging configuration file in '
                             'this format: https://docs.python.org/3/library/'
                             'logging.config.html#logging-config-fileformat '
                             'Setting this overrides -v parameter which uses '
                             ' default logger. (default None)')

    parser.add_argument('--conf', help='Configuration file to load '
                                       '(default ~/' +
                                       NDExUtilConfig.CONFIG_FILE)

    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increases verbosity of logger to standard '
                             'error for log messages in this module and'
                             'in ' + TSV2NICECXMODULE + '. Messages are '
                             'output at these python logging levels '
                             '-v = ERROR, -vv = WARNING, -vvv = INFO, '
                             '-vvvv = DEBUG, -vvvvv = NOTSET (default no '
                             'logging)')
    parser.add_argument('--version', action='version',
                        version=('%(prog)s ' +
                                 ndexbiogridloader.__version__))
    parser.add_argument('--biogridversion',
                        help='Version of BioGRID Release. To see what '
                             'versions are available, visit: '
                             'https://downloads.thebiogrid.org/'
                             'BioGRID/Release-Archive/',
                        default='4.2.191')
    parser.add_argument('--skipdownload', action='store_true',
                        help='If set, skips download of data from BioGRID and '
                             'assumes data already reside in <datadir>'
                             'directory')
    parser.add_argument('--skipupload', action='store_true',
                        help='If set, upload of networks to NDEx is skipped.'
                             'This is mainly for testing purposes')
    parser.add_argument('--organismloadplan',
                        help='Use alternate organism load plan file',
                        default=get_organism_load_plan())
    parser.add_argument('--organismfile', default=get_organismfile(),
                        help='File containing list of organisms to '
                             'upload to NDEx. By default the list '
                             'stored with this tool is used')
    parser.add_argument('--chemicalloadplan',
                        help='Use alternate chemical load plan file',
                        default=get_chemical_load_plan())
    parser.add_argument('--chemicalsfile', default=get_chemicalsfile(),
                        help='File containing list of chemicals to '
                             'upload to NDEx. By default the list '
                             'stored with this tool is used')
    parser.add_argument('--organismstyle',
                        help='Use alternate organism style file',
                        default=get_organism_style())
    parser.add_argument('--chemicalstyle',
                        help='Use alternate chemical style file',
                        default=get_chemical_style())
    parser.add_argument('--noprogressbar', action='store_true',
                        help='If set, disabled tqdm progress'
                             'bar from displaying')
    parser.add_argument('--maxretries', type=int, default=5,
                        help='Number of retries to attempt to upload'
                             'each of network to NDEx')
    parser.add_argument('--retry_sleep', type=int, default=30,
                        help='Number of seconds to wait between '
                             'retry of failed upload of network to NDEx')

    return parser.parse_args(args)


def _setup_logging(args):
    """
    Sets up logging based on parsed command line arguments.
    If args.logconf is set use that configuration otherwise look
    at args.verbose and set logging for this module and the one
    in ndexutil specified by TSV2NICECXMODULE constant
    :param args: parsed command line arguments from argparse
    :raises AttributeError: If args is None or args.logconf is None
    :return: None
    """

    if args.logconf is None:
        level = (50 - (10 * args.verbose))
        logging.basicConfig(format=LOG_FORMAT,
                            level=level)
        logging.getLogger(TSV2NICECXMODULE).setLevel(level)
        logger.setLevel(level)
        return

    # logconf was set use that file
    logging.config.fileConfig(args.logconf,
                              disable_existing_loggers=False)


def _cvtfield(f):
    """
    If str passed in via 'f' parameter is '-' then
    return empty string otherwise return value of 'f'
    :param f:
    :return: empty string if 'f' is '-' otherwise return 'f'
    :rtype: str
    """
    if f is None or f != '-':
        return f
    return ''


class NdexBioGRIDLoader(object):
    """
    Class to load content
    """
    def __init__(self, args):
        """

        :param args:
        """
        self._args = args
        self._datadir = os.path.abspath(args.datadir)
        self._conf_file = args.conf
        self._profile = args.profile
        self._organism_load_plan = args.organismloadplan
        self._chem_load_plan = args.chemicalloadplan

        self._organism_style = args.organismstyle
        self._chem_style = args.chemicalstyle

        self._user = None
        self._pass = None
        self._server = None

        self._ndex = None

        self._biogrid_version = args.biogridversion

        self._datadir = os.path.abspath(args.datadir)

        self._organism_file_name = os.path.join(self._datadir, 'organism.zip')
        self._chemicals_file_name = os.path.join(self._datadir, 'chemicals.zip')

        self._biogrid_organism_file_ext = '-' + self._biogrid_version  + '.tab2.txt'
        self._biogrid_chemicals_file_ext = '-' + self._biogrid_version + '.chemtab.txt'
        self._skipdownload = args.skipdownload
        self._network = None

    def _load_chemical_style_template(self):
        """
        Loads the CX network specified by self._chem_style into self._chem_style_template
        :return:
        """
        self._chem_style_template = ndex2.create_nice_cx_from_file(os.path.abspath(self._chem_style))

    def _load_organism_style_template(self):
        """
        Loads the CX network specified by self._organism_style into self._organism_style_template
        :return:
        """
        self._organism_style_template = ndex2.create_nice_cx_from_file(os.path.abspath(self._organism_style))

    def _get_biogrid_organism_file_name(self, file_extension):
        return 'BIOGRID-ORGANISM-' + self._biogrid_version + file_extension

    def _get_download_url(self):
        return 'https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive/BIOGRID-' + \
               self._biogrid_version + '/'

    def _build_organism_file_url(self):
        url = self._get_download_url() + self._get_biogrid_organism_file_name('.tab2.zip')
        return url

    def _get_chemicals_file_name(self, file_extension):
        return 'BIOGRID-CHEMICALS-' + self._biogrid_version + file_extension

    def _build_chemicals_file_url(self):
        url = self._get_download_url() + self._get_chemicals_file_name('.chemtab.zip')
        return url

    def _parse_config(self):
        """
        Parses config
        :return:
        """
        ncon = NDExUtilConfig(conf_file=self._conf_file)
        con = ncon.get_config()
        self._user = con.get(self._profile, NDExUtilConfig.USER)
        self._pass = con.get(self._profile, NDExUtilConfig.PASSWORD)
        self._server = con.get(self._profile, NDExUtilConfig.SERVER)

    def _get_biogrid_file_name(self, organism_entry):
        return organism_entry[0] + self._biogrid_organism_file_ext

    def _get_biogrid_chemicals_file_name(self, chemical_entry):
        return chemical_entry[0] + self._biogrid_chemicals_file_ext

    def _get_header(self, file_path):

        with open(file_path, 'r') as f_read:
            header_line = f_read.readline().strip()
            header_line_split = header_line.split('\t')

        return header_line_split, 0

    def _download_file(self, url, local_file):
        try:
            response = requests.get(url)
            if response.status_code // 100 == 2:
                with open(local_file, "wb") as received_file:
                    received_file.write(response.content)
            else:
                return response.status_code

        except requests.exceptions.RequestException as e:
            logger.exception('Caught exception: ' + str(e))
            return 2

        return 0

    def _download_biogrid_files(self):
        biogrid_organism_url = self._build_organism_file_url()
        biogrid_chemicals_url = self._build_chemicals_file_url()

        download_status = self._download_file(biogrid_organism_url, self._organism_file_name)
        if (download_status != 0):
            return download_status;

        return self._download_file(biogrid_chemicals_url, self._chemicals_file_name)

    def _get_organism_or_chemicals_file_content(self, type='organism'):
        file_names = []

        path_to_file = self._args.organismfile if type == 'organism' else self._args.chemicalsfile

        with open(path_to_file, 'r') as f:
            for cnt, line in enumerate(f):
                line_split = line.strip().split('\t')
                line_split[1] = line_split[1].replace('"', '')
                file_names.append(line_split)
        return file_names

    def _unzip_biogrid_file(self, file_name, type='organism'):
        try:
            if type == 'organism':
                with zipfile.ZipFile(self._organism_file_name, "r") as zip_ref:
                    extracted_file_path = zip_ref.extract(file_name, self._datadir)
            else:
                with zipfile.ZipFile(self._chemicals_file_name, "r") as zip_ref:
                    extracted_file_path = zip_ref.extract(file_name, self._datadir)

        except Exception as e:
            logger.exception('Caught exception: ' + str(e))
            return 2, None

        return 0, extracted_file_path

    def _remove_biogrid_organism_file(self, file_name):
        try:
            os.remove(file_name)
        except OSError as e:
            logger.error('Caught error removing file: ' +
                         file_name + ' : ' + str(e))
            return e.errno

        return 0

    def _get_header_for_generating_organism_tsv(self):
        header = [
            'Entrez Gene Interactor A',
            'Entrez Gene Interactor B',
            'Official Symbol Interactor A',
            'Official Symbol Interactor B',
            'Synonyms Interactor A',
            'Synonyms Interactor B',
            'Experimental System',
            'Experimental System Type',
            'Pubmed ID',
            'Throughput',
            'Score',
            'Modification',
            'Phenotypes',
            'Qualifications',
            'Organism Interactor A',
            'Organism Interactor B'
        ]
        return header

    def _get_header_for_generating_chemicals_tsv(self):
        header = [
            'Entrez Gene ID',
            'Official Symbol',
            'Synonyms',
            'Action',
            'Interaction Type',
            'Pubmed ID',
            'Chemical Name',
            'Chemical Synonyms',
            'Chemical Source ID',
            'Chemical Type'
        ]
        return header

    def _get_user_agent(self):
        """
        :return:
        """
        return 'biogrid/' + self._biogrid_version

    def _create_ndex_connection(self):
        """
        creates connection to ndex
        :return:
        """
        if self._ndex is None:

            try:
                self._ndex = Ndex2(host=self._server, username=self._user,
                                   password=self._pass,
                                   user_agent=self._get_user_agent())
            except Exception as e:
                self._ndex = None

        return self._ndex

    def _load_network_summaries_for_user(self):
        """
        Gets a dictionary of all networks for user account
        <network name upper cased> => <NDEx UUID>
        :return: 0 if success, 2 otherwise
        """
        self._network_summaries = {}

        try:
            network_summaries = self._ndex.get_network_summaries_for_user(self._user)
        except Exception as e:
            logger.error('Got error trying to get list of'
                         'networks for user: ' + str(e))
            return None, 2

        for summary in network_summaries:
            if summary.get('name') is not None:
                self._network_summaries[summary.get('name').upper()] = summary.get('externalId')

        return self._network_summaries, 0

    def _generate_tsv_from_biogrid_organism_file(self, file_path):

        tsv_file_path = file_path.replace('.tab2.txt', '.tsv')

        with open(file_path, 'r') as f_read:
            next(f_read) # skip header

            pubmed_id_idx = 8
            result = {}
            line_count = 0

            for line in f_read:

                split_line = line.split('\t')

                key = split_line[1] + "," + split_line[2] + "," + split_line[11] + "," + split_line[12] + "," + \
                      split_line[17] + "," + split_line[18] + "," + split_line[19] + "," + split_line[20] + "," + \
                      split_line[21]

                entry = result.get(key)

                if entry:
                    entry[pubmed_id_idx].append(split_line[14])
                else:
                    entry = [split_line[1], split_line[2], split_line[7], split_line[8], \
                             _cvtfield(split_line[9]), _cvtfield(split_line[10]), _cvtfield(split_line[11]),
                             _cvtfield(split_line[12]), [split_line[14]],  # pubmed_ids
                             _cvtfield(split_line[17]), _cvtfield(split_line[18]), _cvtfield(split_line[19]),
                             _cvtfield(split_line[20]), _cvtfield(split_line[21]), split_line[15], split_line[16]]

                    result[key] = entry

                line_count += 1

            with open(tsv_file_path, 'w') as f_output_tsv:
                output_header = '\t'.join(self._get_header_for_generating_organism_tsv()) + '\n'
                f_output_tsv.write(output_header)

                for key, value in result.items():
                    value[pubmed_id_idx] = '|'.join(value[pubmed_id_idx])
                    f_output_tsv.write('\t'.join(value) + "\n")

        return tsv_file_path

    def _generate_tsv_from_biogrid_chemicals_file(self, file_path):

        tsv_file_path = file_path.replace('.chemtab.txt', '.tsv')

        with open(file_path, 'r') as f_read:
            next(f_read)  # skip header

            result = {}
            line_count = 0

            for line in f_read:

                line_count += 1

                split_line = line.split('\t')

                if split_line[6] != '9606':
                    continue

                # add line to hash table
                key = split_line[1] + "," + split_line[13]
                entry = result.get(key)

                if entry:
                    entry[5].append(split_line[11])
                else:

                    chem_synon = "" if split_line[15] == '-' else split_line[15]
                    cas = "" if split_line[22] == '-' else "cas:" + split_line[22]
                    chem_alias = cas
                    if chem_alias:
                        if chem_synon:
                            chem_alias += "|" + chem_synon
                    else:
                        chem_alias = chem_synon

                    entry = [split_line[2], split_line[4], "" if split_line[5] == '-' else \
                        split_line[5], split_line[8], split_line[9], [split_line[11]],
                        split_line[14], chem_alias, split_line[18], split_line[20]]

                    result[key] = entry

            with open(tsv_file_path, 'w') as f_output_tsv:
                output_header = '\t'.join(self._get_header_for_generating_chemicals_tsv()) + '\n'
                f_output_tsv.write(output_header)

                for key, value in result.items():
                    value[5] = '|'.join(value[5])
                    f_output_tsv.write('\t'.join(value) + "\n")

        return tsv_file_path

    def _get_cx_file_path_and_name(self, file_path, organism_or_chemical_entry, type='organism'):
        cx_file_path = file_path.replace('.tab2.txt', '.cx') if type == 'organism' else file_path.replace('.chemtab.txt',
                                                                                                          '.cx')
        cx_file_name_indx = cx_file_path.find(organism_or_chemical_entry[0])

        cx_file_name = cx_file_path[cx_file_name_indx:]

        return cx_file_path, cx_file_name

    def _get_cx_filename(self, path_to_network_in_cx, network_name):
        cx_file_name_indx = path_to_network_in_cx.find(path_to_network_in_cx)
        cx_file_name = path_to_network_in_cx[cx_file_name_indx:]
        return cx_file_name

    def _merge_attributes(self, attribute_list_1, attribute_list_2):

        for attribute1 in attribute_list_1:

            name1 = attribute1['n']

            found = False
            for attribute2 in attribute_list_2:
                if attribute2['n'] == name1:
                    found = True
                    break

            if not found:
                continue

            if attribute1['v'] == attribute2['v']:
                # attriubute with the samae name and value; do not add
                continue

            if not 'd' in attribute1:
                attribute1['d'] = 'list_of_string'
            elif attribute1['d'] == 'boolean':
                attribute1['d'] = 'list_of_boolean'
            elif attribute1['d'] == 'double':
                attribute1['d'] = 'list_of_double'
            elif attribute1['d'] == 'integer':
                attribute1['d'] = 'list_of_integer'
            elif attribute1['d'] == 'long':
                attribute1['d'] = 'list_of_long'
            elif attribute1['d'] == 'string':
                attribute1['d'] = 'list_of_string'

            new_list_of_values = []

            if isinstance(attribute1['v'], list):
                for value in attribute1['v']:
                    if value not in new_list_of_values and value:
                        new_list_of_values.append(value)
            else:
                if attribute1['v'] not in new_list_of_values and attribute1['v']:
                    new_list_of_values.append(attribute1['v'])

            if isinstance(attribute2['v'], list):
                for value in attribute2['v']:
                    if value not in new_list_of_values and value:
                        new_list_of_values.append(value)
            else:
                if attribute2['v'] not in new_list_of_values and attribute2['v']:
                    new_list_of_values.append(attribute2['v'])

            attribute1['v'] = new_list_of_values

    def _collapse_edges(self):

        unique_edges = {}

        # in the loop below, we build a map where key is a tuple (edge_source, interacts, edge_target)
        # and the value is a list of edge ids
        for edge_id, edge in self._network.edges.items():

            edge_key = (edge['s'], edge['i'], edge['t'])
            edge_key_reverse = (edge['t'], edge['i'], edge['s'])

            if edge_key in unique_edges:
                if edge_id not in unique_edges[edge_key]:
                    unique_edges[edge_key].append(edge_id)

            elif edge_key_reverse in unique_edges:
                if edge_id not in unique_edges[edge_key_reverse]:
                    unique_edges[edge_key_reverse].append(edge_id)
            else:
                unique_edges[edge_key] = [edge_id]

        logger.info(len(unique_edges))

        # build collapsed edges and collapsed edges attributes
        # and then use them to replace self._network.edges and self._network.edgeAttributes
        collapsed_edges = {}
        collapsed_edge_attributes = {}

        # create a new edges aspect in collapsed_edges
        for key, list_of_edge_attribute_ids in unique_edges.items():
            edge_id = list_of_edge_attribute_ids.pop(0)
            collapsed_edges[edge_id] = self._network.edges[edge_id]

            if not list_of_edge_attribute_ids:
                collapsed_edge_attributes[edge_id] = self._network.edgeAttributes[edge_id]
                del self._network.edgeAttributes[edge_id]
                continue

            attribute_list = self._network.edgeAttributes[edge_id]

            # here, the list of collapsed edges is not empty, we need to iterate over it
            # and add attributes of the edge(s) to already existing list of edge attributes
            for attribute_id in list_of_edge_attribute_ids:

                attribute_list_for_adding = self._network.edgeAttributes[attribute_id]

                self._merge_attributes(attribute_list, attribute_list_for_adding)

                collapsed_edge_attributes[edge_id] = attribute_list

        del self._network.edges
        self._network.edges = collapsed_edges

        del self._network.edgeAttributes
        self._network.edgeAttributes = collapsed_edge_attributes

    def _using_panda_generate_nice_cx(self, biogrid_file_path, organism_entry, template_network, type='organism'):

        tsv_file_path = self._generate_tsv_from_biogrid_organism_file(biogrid_file_path) if type == 'organism' else \
            self._generate_tsv_from_biogrid_chemicals_file(biogrid_file_path)

        cx_file_path, cx_file_name = self._get_cx_file_path_and_name(biogrid_file_path, organism_entry, type)
        logger.info('started generating {}...'.format(cx_file_name))

        load_plan = self._organism_load_plan if type == 'organism' else self._chem_load_plan

        with open(load_plan, 'r') as lp:
            plan = json.load(lp)

        dataframe = pd.read_csv(tsv_file_path,
                                dtype=str,
                                na_filter=False,
                                delimiter='\t',
                                engine='python')

        network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, plan)

        if type == 'organism':
            network_name = "BioGRID: Protein-Protein Interactions (" + organism_entry[2] + ")"
            network_type = ['interactome', 'ppi']
        else:
            network_name = "BioGRID: Protein-Chemical Interactions (" + organism_entry[2] + ")"
            network_type = ['proteinassociation', 'compoundassociation']

        network.set_name(network_name)

        network.set_network_attribute("description",
                                      template_network.get_network_attribute('description')['v'])

        network.set_network_attribute("reference",
                                      template_network.get_network_attribute('reference')['v'])
        network.set_network_attribute("version", self._biogrid_version)
        network.set_network_attribute("organism", organism_entry[1])
        network.set_network_attribute("networkType", network_type,
                                      'list_of_string')
        network.set_network_attribute("__iconurl",
                                      "https://home.ndexbio.org"
                                      "/img/biogrid_logo.jpg")

        network.apply_style_from_network(template_network)

        self._network = network

        # note, CX file is in memory, but it is not written to file yet
        logger.info(cx_file_name + ' - finished generating')

        # return path where to write CX file abd network name
        return cx_file_path, network_name

    def _upload_cx(self, path_to_network_in_cx, network_name):
        if self._args.skipupload is True:
            logger.info('Skipping upload of "' + network_name +
                        '" network since --skipupload flag is set')
            return 0
        network_uuid = self._network_summaries.get(network_name.upper())

        return self._update_or_upload_with_retry(cxfile=path_to_network_in_cx,
                                                 network_name=network_name,
                                                 network_uuid=network_uuid,
                                                 maxretries=self._args.maxretries,
                                                 retry_sleep=self._args.retry_sleep)

    def _update_or_upload_with_retry(self, cxfile=None,
                                     network_name=None,
                                     network_uuid=None,
                                     maxretries=2,
                                     retry_sleep=5):
        """

        :param cxfile: Path to CX file to upload
        :param network_name: name of network (for logging purposes)
        :param network_uuid: If set method will attempt to update network
                             with UUID passed in. If `None` then new network
                             will be uploaded to NDEx
        :param maxretries: number of retries before giving up
        :return: 0 upon success, 2 upon failure
        :rtype: int
        """
        retry_count = 1
        while retry_count <= maxretries:
            logger.debug('Attempting upload of network try # ' +
                         str(retry_count))
            with open(cxfile, 'rb') as network_out:
                try:
                    if network_uuid is None:
                        self._ndex.save_cx_stream_as_new_network(network_out)
                    else:
                        self._ndex.update_cx_network(network_out, network_uuid)
                    return 0
                except Exception as e:
                    logger.info('Caught exception attempting to '
                                'upload network : ' + str(e))
                    logger.debug('Sleeping ' + str(retry_sleep) +
                                 ' seconds')
                    time.sleep(retry_sleep)
            retry_count += 1
        logger.error('Unable to upload ' + str(network_name) +
                     ' network after ' + str(maxretries) + ' retries.')
        return 2

    def _check_if_data_dir_exists(self):
        data_dir_existed = True

        if not os.path.exists(self._datadir):
            data_dir_existed = False
            os.makedirs(self._datadir, mode=0o755)

        return data_dir_existed

    def _write_nice_cx_to_file(self, cx_file_path):

        logger.info('started writing network "{}" to disk...'.
                    format(self._network.get_name()))

        with open(cx_file_path, 'w') as f:
            json.dump(self._network.to_cx(), f)

        logger.info('finished writing network "{}" to disk'.
                    format(self._network.get_name()))

    def run(self):
        """
        Runs content loading for NDEx BioGRID Content Loader
        :param theargs:
        :return:
        """
        self._parse_config()

        self._create_ndex_connection()

        data_dir_existed = self._check_if_data_dir_exists()

        if self._skipdownload is False or data_dir_existed is False:
            logger.info('Downloading biogrid files')
            download_status = self._download_biogrid_files()
            if download_status != 0:
                return download_status

        net_summaries, status_code = self._load_network_summaries_for_user()
        if status_code != 0:
            return status_code

        self._load_organism_style_template()
        self._load_chemical_style_template()
        upload_exit_codes = set()
        organism_file_entries = self._get_organism_or_chemicals_file_content('organism')
        for entry in tqdm(organism_file_entries,
                          desc='Organisms',
                          disable=self._args.noprogressbar):
            file_name = self._get_biogrid_file_name(entry)

            logger.debug('Unzipping biogrid file: ' + file_name)
            status_code,\
                biogrid_organism_file_path = self._unzip_biogrid_file(file_name,
                                                                      'organism')

            if status_code == 0:

                logger.info('Creating CX for ' + str(entry))
                cx_file_path,\
                    network_name = self._using_panda_generate_nice_cx(biogrid_organism_file_path,
                                                                      entry, self._organism_style_template, 'organism')

                self._collapse_edges()
                logger.info('Applying spring layout for ' + str(entry))
                self._apply_simple_spring_layout(self._network)
                logger.info('Writing CX to file for ' + str(entry))
                self._write_nice_cx_to_file(cx_file_path)
                logger.info('Uploading CX to NDEx for ' + str(entry))
                upload_exit_codes.add(self._upload_cx(cx_file_path,
                                                      network_name))
            else:
                upload_exit_codes.add(9)
                logger.error('Unable to extract ' + file_name + ' from archive')

        chemical_file_entries = self._get_organism_or_chemicals_file_content('chemicals')

        for entry in tqdm(chemical_file_entries, desc='Chemicals',
                          disable=self._args.noprogressbar):
            file_name = self._get_biogrid_chemicals_file_name(entry)

            status_code, biogrid_chemicals_file_path = self._unzip_biogrid_file(file_name,
                                                                                'chemicals')

            if status_code == 0:
                logger.info('Creating CX for ' + str(entry))
                cx_file_path,\
                    network_name = self._using_panda_generate_nice_cx(biogrid_chemicals_file_path,
                                                                      entry,
                                                                      self._chem_style_template,
                                                                      'chemical')
                self._collapse_edges()
                logger.info('Applying spring layout for ' + str(entry))
                self._apply_simple_spring_layout(self._network)
                logger.info('Writing CX to file for ' + str(entry))
                self._write_nice_cx_to_file(cx_file_path)
                logger.info('Uploading CX to NDEx for ' + str(entry))
                upload_exit_codes.add(self._upload_cx(cx_file_path,
                                                      network_name))
            else:
                upload_exit_codes.add(10)
                logger.error('Unable to extract ' + file_name + ' from archive')
        return max(upload_exit_codes)

    def _apply_simple_spring_layout(self, network, iterations=5):
        """
        Applies simple spring network by using
        :py:func:`networkx.drawing.spring_layout` and putting the
        coordinates into 'cartesianLayout' aspect on the 'network' passed
        in

        :param network: Network to update
        :type network: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param iterations: Number of iterations to use for networkx spring
                           layout call
        :type iterations: int
        :return: None
        """
        num_nodes = len(network.get_nodes())
        logger.debug('Converting network to networkx')
        my_networkx = network.to_networkx(mode='default')
        if num_nodes < 10:
            nodescale = num_nodes*20
        elif num_nodes < 20:
            nodescale = num_nodes*15
        elif num_nodes < 100:
            nodescale = num_nodes*10
        else:
            nodescale = num_nodes*5
        logger.debug('Applying spring layout')
        my_networkx.pos = nx.drawing.spring_layout(my_networkx,
                                                   scale=nodescale,
                                                   k=1.8,
                                                   iterations=iterations)
        cartesian_aspect = self._cartesian(my_networkx)
        network.set_opaque_aspect("cartesianLayout", cartesian_aspect)
        del my_networkx

    def _cartesian(self, g):
        """
        Converts node coordinates from a :py:class:`networkx.Graph` object
        to a list of dicts with following format:

        [{'node': <node id>,
          'x': <x position>,
          'y': <y position>}]

        :param g:
        :return: coordinates
        :rtype: list
        """
        return [{'node': n,
                 'x': float(g.pos[n][0]),
                 'y': float(g.pos[n][1])} for n in g.pos]


def main(args):
    """
    Main entry point for program
    :param args:
    :return:
    """
    desc = """
    Version {version}

    Loads NDEx BioGRID Content Loader data into NDEx (http://ndexbio.org).

    To connect to NDEx server a configuration file must be passed
    into --conf parameter. If --conf is unset the configuration
    the path ~/{confname} is examined.

    The configuration file should be formatted as follows:

    [<value in --profile (default ndexbiogridloader)>]

    {user} = <NDEx username>
    {password} = <NDEx password>
    {server} = <NDEx server(omit http) ie public.ndexbio.org>


    """.format(confname=NDExUtilConfig.CONFIG_FILE,
               user=NDExUtilConfig.USER,
               password=NDExUtilConfig.PASSWORD,
               server=NDExUtilConfig.SERVER,
               version=ndexbiogridloader.__version__)
    theargs = _parse_arguments(desc, args[1:])
    theargs.program = args[0]
    theargs.version = ndexbiogridloader.__version__

    try:
        _setup_logging(theargs)
        loader = NdexBioGRIDLoader(theargs)
        return loader.run()
    except Exception as e:
        logger.exception('Caught exception', e)
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
