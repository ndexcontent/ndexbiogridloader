#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ndexbiogridloader` package."""

import os
import tempfile
import shutil

import unittest
from ndexutil.config import NDExUtilConfig
from ndexbiogridloader import ndexloadbiogrid

from ndexbiogridloader.ndexloadbiogrid import NdexBioGRIDLoader


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class TestNdexbiogridloader(unittest.TestCase):
    ClassIsSetup = False

    """Tests for `ndexbiogridloader` package."""

    def setupClass(self):
        unittest.TestCase.setUp(self)

        self.__class__._data_dir = ndexloadbiogrid.get_datadir()
        self.__class__._testing_dir = ndexloadbiogrid.get_testsdir()
        self.__class__._biogrid_files_dir = os.path.join(self.__class__._testing_dir, 'biogrid_files')

        self._the_args = {
            'profile': 'ndexbiogridloader',
            'biogridversion': '3.5.172',
            'datadir': self.__class__._biogrid_files_dir,
            'organismloadplan': ndexloadbiogrid.get_organism_load_plan(),
            'chemicalloadplan': ndexloadbiogrid.get_chemical_load_plan()

        }

        self._the_args = dotdict(self._the_args)
        self.__class__.NdexBioGRIDLoader = NdexBioGRIDLoader(self._the_args)
        self.__class__.NdexBioGRIDLoader._parse_config()

        self.__class__.organism_entries_expected = [
            ['BIOGRID-ORGANISM-Zea_mays', 'Maize, 4577, Zea mays', 'Z. mays'],
            ['BIOGRID-ORGANISM-Xenopus_laevis', 'African clawed frog, 8355, Xenopus laevis', 'X. laevis'],
            ['BIOGRID-ORGANISM-Saccharomyces_cerevisiae_S288c', 'Baker\'s yeast, 559292', 'S. cerevisiae'],
            ['BIOGRID-ORGANISM-Rattus_norvegicus', 'Norway rat, 10116, Rattus norvegicus',  'R. norvegicus'],
            ['BIOGRID-ORGANISM-Mus_musculus', 'House mouse, 10090, Mus musculus', 'M. musculus'],
            ['BIOGRID-ORGANISM-Human_papillomavirus_16', 'HPV, 10566, Human papillomavirus', 'HPV'],
            ['BIOGRID-ORGANISM-Human_Immunodeficiency_Virus_2', 'HIV-2, 11709, Human immunodeficiency virus 2', 'HIV-2'],
            ['BIOGRID-ORGANISM-Human_Immunodeficiency_Virus_1', 'HIV-1, 11676, Human immunodeficiency virus 1', 'HIV-1'],
            ['BIOGRID-ORGANISM-Homo_sapiens', 'Human, 9606, Homo sapiens', 'H. sapiens'],
            ['BIOGRID-ORGANISM-Drosophila_melanogaster', 'Fruit fly, 7227, Drosophila melanogaster', 'D. melanogaster'],
            ['BIOGRID-ORGANISM-Danio_rerio',  'Zebrafish, 7955, Danio rerio',  'D. rerio'],
            ['BIOGRID-ORGANISM-Caenorhabditis_elegans', 'Roundworm, 6239, Cenorhabditis elegans', 'C. elegans'],
            ['BIOGRID-ORGANISM-Arabidopsis_thaliana_Columbia', 'Thale cress, 3702, Arabidopsis thaliana', 'A. thaliana']
        ]

        self.__class__.chemicals_entries_expected = [
            ['BIOGRID-CHEMICALS', 'Human, 9606, Homo sapiens', 'H. sapiens']
        ]

        self.__class__._style = {
            'protein_uuid': '584f67d3-817b-11e9-917e-525400c25d22',
            'chem_uuid': '5df4b7d5-817b-11e9-917e-525400c25d22'
        }

        self.__class__._ndex = self.NdexBioGRIDLoader._create_ndex_connection()
        self.assertIsNotNone(self.__class__._ndex, 'Unable to to create NDEx client connection')



    def setUp(self):
        """Set up test fixtures, if any."""
        if not self.ClassIsSetup:
            self.setupClass()
            self.__class__.ClassIsSetup = True

        self.organism_file_entries = self.NdexBioGRIDLoader._get_organism_or_chemicals_file_content()
        self.assertListEqual(self.organism_entries_expected, self.organism_file_entries)

        self.chemicals_file_entries = self.NdexBioGRIDLoader._get_organism_or_chemicals_file_content('chemicals')
        self.assertListEqual(self.chemicals_entries_expected, self.chemicals_file_entries)


    def tearDown(self):
        """Tear down test fixtures, if any."""


    @unittest.skip("skipping test_02")
    def test_02_header_for_generated_tsv_file(self):

        expected_header =  [
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
            'Organism Interactor B',
        ]
        actual_header = self.NdexBioGRIDLoader._get_header_for_generating_organism_tsv()

        self.assertListEqual(expected_header, actual_header)

    @unittest.skip("skipping test_03")
    def test_03_check_biogrid_organism_file_format(self):
        expected_header = [
            '#BioGRID Interaction ID',
            'Entrez Gene Interactor A',
            'Entrez Gene Interactor B',
            'BioGRID ID Interactor A',
            'BioGRID ID Interactor B',
            'Systematic Name Interactor A',
            'Systematic Name Interactor B',
            'Official Symbol Interactor A',
            'Official Symbol Interactor B',
            'Synonyms Interactor A',
            'Synonyms Interactor B',
            'Experimental System',
            'Experimental System Type',
            'Author',
            'Pubmed ID',
            'Organism Interactor A',
            'Organism Interactor B',
            'Throughput',
            'Score',
            'Modification',
            'Phenotypes',
            'Qualifications',
            'Tags',
            'Source Database'
        ]

        for entry in self.organism_file_entries:

            file_name = self.NdexBioGRIDLoader._get_biogrid_file_name(entry)

            status_code, file_path = self.NdexBioGRIDLoader._unzip_biogrid_file(file_name, 'organism')

            with self.subTest():
                self.assertEqual(status_code, 0, 'Unable to extract ' + file_name + ' from archive')

                with open(file_path) as f_read:

                    header = f_read.readline().strip()
                    header_split = header.split('\t')

                    self.assertListEqual(expected_header, header_split)

            if status_code == 0:
                self.NdexBioGRIDLoader._remove_biogrid_organism_file(file_path)


    @unittest.skip("skipping test_04")
    def test_04_get_style_templates_from_NDEx(self):
        protein_template, status_code = self.NdexBioGRIDLoader._get_network_from_NDEx(self.__class__._style['protein_uuid'])
        self.assertEqual(status_code, 0, 'Unable to get protein style network UUID ' + self.__class__._style['protein_uuid'])

        chem_template, status_code = self.NdexBioGRIDLoader._get_network_from_NDEx(self.__class__._style['chem_uuid'])
        self.assertEqual(status_code, 0, 'Unable to get chem style network UUID ' + self.__class__._style['chem_uuid'])


    @unittest.skip("skipping test_05")
    def test_05_get_network_summaries(self):
        net_summaries, status_code = self.NdexBioGRIDLoader._load_network_summaries_for_user()
        self.assertEqual(status_code, 0, 'Unable to get netwok summaries')



    @unittest.skip("skipping test_06")
    def test_06_generate_organism_CX_and_upload(self):

        status_code = self.NdexBioGRIDLoader._download_biogrid_files()
        self.assertEqual(status_code, 0, 'Unable to download required biogrid files ')


        protein_template, status_code = self.NdexBioGRIDLoader._get_network_from_NDEx(self.__class__._style['protein_uuid'])
        self.assertEqual(status_code, 0, 'Unable to get protein style network UUID ' + self.__class__._style['protein_uuid'])


        net_summaries, status_code = self.NdexBioGRIDLoader._load_network_summaries_for_user()
        self.assertEqual(status_code, 0, 'Unable to get netwok summaries')


        expected_organism_header =  [
            '#BioGRID Interaction ID',
            'Entrez Gene Interactor A',
            'Entrez Gene Interactor B',
            'BioGRID ID Interactor A',
            'BioGRID ID Interactor B',
            'Systematic Name Interactor A',
            'Systematic Name Interactor B',
            'Official Symbol Interactor A',
            'Official Symbol Interactor B',
            'Synonyms Interactor A',
            'Synonyms Interactor B',
            'Experimental System',
            'Experimental System Type',
            'Author',
            'Pubmed ID',
            'Organism Interactor A',
            'Organism Interactor B',
            'Throughput',
            'Score',
            'Modification',
            'Phenotypes',
            'Qualifications',
            'Tags',
            'Source Database'
        ]


        #iteration = 1
        for entry in self.organism_file_entries:

            #if 1 != iteration:
            #    continue
            #iteration += 1

            file_name = self.NdexBioGRIDLoader._get_biogrid_file_name(entry)

            status_code, biogrid_organism_file_path = self.NdexBioGRIDLoader._unzip_biogrid_file(file_name, 'organism')

            with self.subTest():
                self.assertEqual(status_code, 0, 'Unable to extract ' + file_name + ' from archive')

                header, status_code_1 = self.NdexBioGRIDLoader._get_header(biogrid_organism_file_path)
                self.assertEqual(status_code_1, 0, 'Unable to get header from ' + biogrid_organism_file_path)
                self.assertListEqual(expected_organism_header, header)


                biogrid_organism_CX_path, network_name, status_code_1, = \
                    self.NdexBioGRIDLoader._generate_CX_from_biogrid_organism_file(biogrid_organism_file_path, entry, \
                                                                                   protein_template)
                self.assertEqual(status_code_1, 0, 'Unable to generate CX from ' + biogrid_organism_file_path)


                status_code1 = self.NdexBioGRIDLoader._upload_CX(biogrid_organism_CX_path, network_name)
                self.assertEqual(status_code_1, 0, 'Unable to upload ' + network_name)




    #@unittest.skip("skipping test_07")
    def test_07_using_panda_generate_CX_network_from_biogrid_organism_files(self):

        protein_template, status_code = self.NdexBioGRIDLoader._get_network_from_NDEx(self.__class__._style['protein_uuid'])
        self.assertEqual(status_code, 0, 'Unable to get protein style network UUID ' + self.__class__._style['protein_uuid'])

        net_summaries, status_code = self.NdexBioGRIDLoader._load_network_summaries_for_user()
        self.assertEqual(status_code, 0, 'Unable to get netwok summaries')

        template_uuid = self.__class__._style['protein_uuid']

        iteration = 1
        for entry in self.organism_file_entries:
            # if 1 != iteration:
            #    continue
            iteration += 1

            file_name = self.NdexBioGRIDLoader._get_biogrid_file_name(entry)

            status_code, biogrid_organism_file_path = self.NdexBioGRIDLoader._unzip_biogrid_file(file_name, 'organism')

            with self.subTest():
                self.assertEqual(status_code, 0, 'Unable to extract ' + file_name + ' from archive')

                status_code_1 = self.NdexBioGRIDLoader._using_panda_generate_and_upload_CX(\
                        biogrid_organism_file_path, entry, protein_template, template_uuid, 'organism')

                self.assertEqual(status_code_1, 0, 'Unable to generate CX from ' + biogrid_organism_file_path)


    #@unittest.skip("skipping test_08")
    def test_08_using_panda_generate_CX_network_from_biogrid_chemical_files(self):

        chem_template, status_code = self.NdexBioGRIDLoader._get_network_from_NDEx(self.__class__._style['chem_uuid'])
        self.assertEqual(status_code, 0, 'Unable to get protein style network UUID ' + self.__class__._style['chem_uuid'])

        net_summaries, status_code = self.NdexBioGRIDLoader._load_network_summaries_for_user()
        self.assertEqual(status_code, 0, 'Unable to get netwok summaries')

        template_uuid = self.__class__._style['chem_uuid']

        iteration = 1
        for entry in self.chemicals_file_entries:
            # if 1 != iteration:
            #    continue
            iteration += 1

            file_name = self.NdexBioGRIDLoader._get_biogrid_chemicals_file_name(entry)

            status_code, biogrid_chemical_file_path = self.NdexBioGRIDLoader._unzip_biogrid_file(file_name, 'chemical')

            with self.subTest():
                self.assertEqual(status_code, 0, 'Unable to extract ' + file_name + ' from archive')

                status_code_1 = self.NdexBioGRIDLoader._using_panda_generate_and_upload_CX(\
                        biogrid_chemical_file_path, entry, chem_template, template_uuid, 'chemical')

                self.assertEqual(status_code_1, 0, 'Unable to generate CX from ' + biogrid_chemical_file_path)



    @unittest.skip("skipping test_21")
    def test_20_generate_chemicals_CX_and_upload(self):

        expected_chemical_header = [
            '#BioGRID Chemical Interaction ID',
            'BioGRID Gene ID',
            'Entrez Gene ID',
            'Systematic Name',
            'Official Symbol',
            'Synonyms',
            'Organism ID',
            'Organism',
            'Action',
            'Interaction Type',
            'Author',
            'Pubmed ID',
            'BioGRID Publication ID',
            'BioGRID Chemical ID',
            'Chemical Name',
            'Chemical Synonyms',
            'Chemical Brands',
            'Chemical Source',
            'Chemical Source ID',
            'Molecular Formula',
            'Chemical Type',
            'ATC Codes',
            'CAS Number',
            'Curated By',
            'Method',
            'Method Description',
            'Related BioGRID Gene ID',
            'Related Entrez Gene ID',
            'Related Systematic Name',
            'Related Official Symbol',
            'Related Synonyms',
            'Related Organism ID',
            'Related Organism',
            'Related Type',
            'Notes'
        ]

        net_summaries, status_code = self.NdexBioGRIDLoader._load_network_summaries_for_user()
        self.assertEqual(status_code, 0, 'Unable to get netwok summaries')

        chemical_template, status_code = self.NdexBioGRIDLoader._get_network_from_NDEx(self.__class__._style['chem_uuid'])
        self.assertEqual(status_code, 0, 'Unable to get chemicals style network UUID ' + self.__class__._style['chem_uuid'])


        for entry in self.chemicals_file_entries:

            file_name = self.NdexBioGRIDLoader._get_biogrid_chemicals_file_name(entry)

            status_code, biogrid_chemicals_file_path = self.NdexBioGRIDLoader._unzip_biogrid_file(file_name, 'chemicals')

            with self.subTest():
                self.assertEqual(status_code, 0, 'Unable to extract ' + file_name + ' from archive')

                header, status_code_1 = self.NdexBioGRIDLoader._get_header(biogrid_chemicals_file_path)
                self.assertEqual(status_code_1, 0, 'Unable to get header from ' + biogrid_chemicals_file_path)
                self.assertListEqual(expected_chemical_header, header)

                biogrid_chemicals_CX_path, network_name, status_code_1, = \
                    self.NdexBioGRIDLoader._generate_CX_from_biogrid_chemicals_file(biogrid_chemicals_file_path, entry, \
                                                                                    chemical_template)
                self.assertEqual(status_code_1, 0, 'Unable to generate CX from ' + biogrid_chemicals_file_path)





