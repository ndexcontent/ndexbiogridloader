#! /usr/bin/env python

import argparse
import sys
import logging
from logging import config
from ndexutil.config import NDExUtilConfig
import ndexbiogridloader

import requests
import os
import zipfile

import urllib3, shutil
import ndex2
from ndex2.client import Ndex2

from ndexutil.tsv.streamtsvloader import StreamTSVLoader

logger = logging.getLogger(__name__)

from datetime import datetime

TSV2NICECXMODULE = 'ndexutil.tsv.tsv2nicecx2'

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"


import json
import pandas as pd
import ndexutil.tsv.tsv2nicecx2 as t2n


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

def get_testsdir():
    """
    Constructs the testing directory path
    :return: path to testing dir
    :rtype: string
    """
    _parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    return os.path.join(_parent_dir, TESTSDIR)

def get_datadir():
    """
    Gets the directory where BioGRID archived files will be downloaded to and processed
    :return: path to dir
    :rtype: string
    """
    return os.path.join(get_package_dir(), DATADIR)


def _parse_arguments(desc, args):
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    help_fm = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=help_fm)
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

    parser.add_argument('--biogridversion', help='Version of BioGRID Release', default='3.5.172')

    parser.add_argument('--datadir', help='Directory where BioGRID files will be downloaded and processed',
                                          default=get_datadir())

    parser.add_argument('--organismloadplan', help='Use alternate organism load plan file', default=get_organism_load_plan())

    parser.add_argument('--chemicalloadplan', help='Use alternate chemical load plan file', default=get_chemical_load_plan())

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
    return '' if f == '-' else f

class NdexBioGRIDLoader(object):
    """
    Class to load content
    """
    def __init__(self, args):
        """

        :param args:
        """
        self._conf_file = args.conf
        self._profile = args.profile
        self._organism_load_plan = args.organismloadplan
        self._chem_load_plan = args.chemicalloadplan




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

        #self._organism_file


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

            self._protein_template_id = con.get(self._profile, 'style_protein')
            self._chemical_template_id = con.get(self._profile, 'style_chem')

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

        if not os.path.exists(self._datadir):
            os.makedirs(self._datadir)

        try:
            response = requests.get(url)
            if response.status_code // 100 == 2:
                with open(local_file, "wb") as received_file:
                    received_file.write(response.content)
            else:
                return response.status_code

        except requests.exceptions.RequestException as e:
            logger.exception('Caught exception')
            print('\n\n\tException: {}\n'.format(e))
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

        path_to_file = get_organismfile() if type == 'organism' else get_chemicalsfile()

        with open(path_to_file, 'r') as f:
            for cnt, line in enumerate(f):
                line_split = line.strip().split('\t')
                line_split[1] = line_split[1].replace('"', '')
                #line_split[0] = line_split[0] + '-' + self._biogrid_version + '.tab2.txt'

                #file_name = (line.split('\t'))[0]
                #organism_file_name = file_name.strip() + '-' + self._biogrid_version + '.tab2.txt'
                file_names.append(line_split)

        #file_names.reverse()
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
            print('\n\n\tException: {}\n'.format(e))
            return 2, None

        return 0, extracted_file_path



    def _remove_biogrid_organism_file(self, file_name):
        try:
            os.remove(file_name)
        except OSError as e:
            return e.errno

        return 0

    def _get_header_for_generating_organism_tsv(self):
        header =  [
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
        header =  [
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
                                   password=self._pass, user_agent=self._get_user_agent())
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
            return None, 2

        for summary in network_summaries:
            if summary.get('name') is not None:
                self._network_summaries[summary.get('name').upper()] = summary.get('externalId')

        return self._network_summaries, 0


    def _generate_TSV_from_biogrid_organism_file(self, file_path):

        tsv_file_path = file_path.replace('.tab2.txt', '.tsv')

        with open(file_path, 'r') as f_read:
            next(f_read) # skip header

            pubmed_id_idx = 8
            result = {}
            line_count = 0

            for line in f_read:

                split_line = line.split('\t')

                key = split_line[1] + ","  + split_line[2] + "," + split_line[11] + "," + split_line[12] + "," + \
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


    def _generate_TSV_from_biogrid_chemicals_file(self, file_path):

        tsv_file_path = file_path.replace('.chemtab.txt', '.tsv')

        with open(file_path, 'r') as f_read:
            next(f_read)  # skip header

            result = {}
            line_count = 0

            for line in f_read:

                line_count += 1

                split_line = line.split('\t')

                if (split_line[6] != '9606'):
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


    def _get_CX_file_path_and_name(self, file_path, organism_or_chemical_entry, type='organism'):

        cx_file_path = file_path.replace('.tab2.txt', '.cx') if type == 'organism' else file_path.replace('.chemtab.txt', '.cx')

        cx_file_name_indx = cx_file_path.find(organism_or_chemical_entry[0])

        cx_file_name = cx_file_path[cx_file_name_indx:]

        return cx_file_path, cx_file_name


    def _get_CX_filename(self, path_to_network_in_CX, network_name):
        cx_file_name_indx = path_to_network_in_CX.find(path_to_network_in_CX)
        cx_file_name = path_to_network_in_CX[cx_file_name_indx:]
        return cx_file_name



    def _generate_CX_from_TSV(self, file_path, tsv_file_path, template, organism_or_chemical_entry, type='organism'):

        cx_file_path, cx_file_name = self._get_CX_file_path_and_name(file_path, organism_or_chemical_entry, type)

        print('\n{} - started generating {}...'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), cx_file_name))

        with open(tsv_file_path, 'r') as tsvfile:

            with open(cx_file_path, "w") as out:

                load_plan = self._organism_load_plan if type == 'organism' else self._chem_load_plan
                loader = StreamTSVLoader(load_plan, template)

                if type == 'organism':
                    network_name =  "BioGRID: Protein-Protein Interactions (" + organism_or_chemical_entry[2] + ")"
                    networkType = 'Protein-Protein Interaction'
                else:
                    network_name =  "BioGRID: Protein-Chemical Interactions (" + organism_or_chemical_entry[2] + ")"
                    networkType = 'Protein-Chemical Interaction'

                organism = organism_or_chemical_entry[1]

                try:
                    loader.write_cx_network(tsvfile, out,
                                            [
                                                {'n': 'name', 'v': network_name},
                                                {'n': 'description',
                                                 'v': template.get_network_attribute('description')['v']},
                                                {'n': 'reference',
                                                 'v': template.get_network_attribute('reference')['v']},
                                                {'n': 'version', 'v': self._biogrid_version},
                                                {'n': 'organism', 'v': organism},
                                                {'n': 'networkType', 'v': networkType}
                                            ])
                except Exception as e:

                    print('{} - unable to generate {}: {}'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                               cx_file_name, e))
                    return None, network_name, 2

                else:
                    print('{} - finished generating {}'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                             cx_file_name))

        return cx_file_path, network_name, 0


    def _get_network_from_NDEx(self, network_UUID):
        try:
            network = ndex2.create_nice_cx_from_server(server=self._server,
                                                       uuid=network_UUID,
                                                       username=self._user,
                                                       password=self._pass)
        except Exception as e:
            return None, 2

        return network, 0


    def _generate_CX_from_biogrid_organism_file(self, biogrid_file_path, organism_entry, template_network):

        tsv_file_path = self._generate_TSV_from_biogrid_organism_file(biogrid_file_path)

        cx_file_path, network_name, status_code = \
            self._generate_CX_from_TSV(biogrid_file_path, tsv_file_path, template_network, organism_entry, 'organism')

        return cx_file_path, network_name, status_code


    def _generate_CX_from_biogrid_chemicals_file(self, biogrid_file_path, organism_entry, template_network):

        tsv_file_path = self._generate_TSV_from_biogrid_chemicals_file(biogrid_file_path)

        cx_file_path, network_name, status_code = \
            self._generate_CX_from_TSV(biogrid_file_path, tsv_file_path, template_network, organism_entry, 'chemical')

        return cx_file_path, network_name, status_code



    def _using_panda_generate_and_upload_CX(self, biogrid_file_path, organism_entry, template_network, template_uuid, type='organism'):

        tsv_file_path = self._generate_TSV_from_biogrid_organism_file(biogrid_file_path) if type == 'organism' else \
            self._generate_TSV_from_biogrid_chemicals_file(biogrid_file_path)

        load_plan = self._organism_load_plan if type == 'organism' else self._chem_load_plan

        with open(load_plan, 'r') as lp:
            plan = json.load(lp)

            dataframe = pd.read_csv(tsv_file_path,
                                    dtype=str,
                                    na_filter=False,
                                    delimiter='\t',
                                    engine='python')

            network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, plan)

            organism = organism_entry[1]

            if type == 'organism':
                network_name = "BioGRID: Protein-Protein Interactions (" + organism_entry[2] + ")"
                networkType = 'Protein-Protein Interaction'
            else:
                network_name = "BioGRID: Protein-Chemical Interactions (" + organism_entry[2] + ")"
                networkType = 'Protein-Chemical Interaction'

            network.set_name(network_name)

            network.set_network_attribute("description",
                                          template_network.get_network_attribute('description')['v'])

            network.set_network_attribute("reference",
                                          template_network.get_network_attribute('reference')['v'])
            network.set_network_attribute("version", self._biogrid_version)
            network.set_network_attribute("organism", organism_entry[1])
            network.set_network_attribute("networkType", networkType)

            network.apply_template(username=self._user, password=self._pass, server=self._server,
                                   uuid=template_uuid)

            network_UUID = self._network_summaries.get(network_name.upper())

            if network_UUID is None:
                print('\n{} - started uploading {}...'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                              network_name))
                network.upload_to(self._server, self._user, self._pass)
                print('{} - finished uploading {}'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                          network_name))
            else:
                print('\n{} - started updating {}...'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                             network_name))
                network.update_to(network_UUID, self._server, self._user, self._pass)
                print('{} - finished updating {}'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                         network_name))

        return 0


    def _upload_CX(self, path_to_network_in_CX, network_name):

        network_UUID = self._network_summaries.get(network_name.upper())

        cx_file_name = self._get_CX_filename(path_to_network_in_CX, network_name)

        with open(path_to_network_in_CX, 'br') as network_out:
            try:
                if network_UUID is None:
                    print('\n{} - started uploading {}...'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                                   cx_file_name))
                    self._ndex.save_cx_stream_as_new_network(network_out)
                    print('{} - finished uploading {}'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                               cx_file_name))
                else:
                    print('\n{} - started updating {}...'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                                  cx_file_name))
                    self._ndex.update_cx_network(network_out, network_UUID)
                    print('{} - finished updating {}'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                               cx_file_name))

            except Exception as e:
                print('{} - unable to update or upload {}'.format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                                         cx_file_name))
                print(e)
                return 2

        return 0


    def run(self):
        """
        Runs content loading for NDEx BioGRID Content Loader
        :param theargs:
        :return:
        """
        self._parse_config()

        self._create_ndex_connection()
        self._load_network_summaries_for_user()

        self._download_biogrid_files()

        #self._unzip_biogrid_files()

        return 0

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

    [<value in --profile (default ncipid)>]

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
        logger.exception('Caught exception')
        print('\n\n\tException: {}\n'.format(e))
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
