#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ndexbiogridloader` package."""

import os
import tempfile
import shutil

from unittest.mock import MagicMock
import unittest
import ndex2
from ndex2.nice_cx_network import NiceCXNetwork
from ndexutil.config import NDExUtilConfig
from ndexbiogridloader import ndexloadbiogrid
from ndexbiogridloader.ndexloadbiogrid import NdexBioGRIDLoader


class TestNdexbiogridloader(unittest.TestCase):
    """Tests for `ndexbiogridloader` package."""

    def setUp(self):
        """setup"""
        pass

    def tearDown(self):
        """Tear down test fixtures, if any."""
        pass

    def test_get_package_dir(self):
        res = ndexloadbiogrid.get_package_dir()
        self.assertTrue(os.path.isdir(res))

    def test_get_organism_style(self):
        res = ndexloadbiogrid.get_organism_style()
        self.assertTrue(os.path.isfile(res))
        net = ndex2.create_nice_cx_from_file(res)
        props = net.get_opaque_aspect('cyVisualProperties')
        self.assertTrue(isinstance(props, list))

    def test_get_chemical_style(self):
        res = ndexloadbiogrid.get_chemical_style()
        self.assertTrue(os.path.isfile(res))
        net = ndex2.create_nice_cx_from_file(res)
        props = net.get_opaque_aspect('cyVisualProperties')
        self.assertTrue(isinstance(props, list))

    def test_get_organism_load_plan(self):
        res = ndexloadbiogrid.get_organism_load_plan()
        self.assertTrue(os.path.isfile(res))

    def test_get_chemical_load_plan(self):
        res = ndexloadbiogrid.get_chemical_load_plan()
        self.assertTrue(os.path.isfile(res))

    def test_get_organismfile(self):
        res = ndexloadbiogrid.get_organismfile()
        self.assertTrue(os.path.isfile(res))

    def test_get_chemicalsfile(self):
        res = ndexloadbiogrid.get_chemicalsfile()
        self.assertTrue(os.path.isfile(res))

    def test_parse_arguments_defaults(self):
        fakeargs = ['datadir']
        pargs = ndexloadbiogrid._parse_arguments('desc', fakeargs)
        self.assertEqual('datadir', pargs.datadir)
        self.assertEqual('ndexbiogridloader', pargs.profile)
        self.assertEqual('4.2.191', pargs.biogridversion)
        self.assertEqual(ndexloadbiogrid.get_organism_load_plan(),
                         pargs.organismloadplan)
        self.assertEqual(ndexloadbiogrid.get_chemical_load_plan(),
                         pargs.chemicalloadplan)
        self.assertEqual(ndexloadbiogrid.get_organism_style(),
                         pargs.organismstyle)
        self.assertEqual(ndexloadbiogrid.get_chemical_style(),
                         pargs.chemicalstyle)

    def test_parse_arguments_custom(self):
        fakeargs = ['datadir', '--biogridversion', '1',
                    '--organismloadplan', 'organismplan',
                    '--chemicalloadplan', 'chemicalplan',
                    '--organismstyle', 'organismstyle',
                    '--chemicalstyle', 'chemicalstyle']
        pargs = ndexloadbiogrid._parse_arguments('desc', fakeargs)
        self.assertEqual('datadir', pargs.datadir)
        self.assertEqual('ndexbiogridloader', pargs.profile)
        self.assertEqual('1', pargs.biogridversion)
        self.assertEqual('organismplan',
                         pargs.organismloadplan)
        self.assertEqual('chemicalplan',
                         pargs.chemicalloadplan)
        self.assertEqual('organismstyle',
                         pargs.organismstyle)
        self.assertEqual('chemicalstyle',
                         pargs.chemicalstyle)

    def test_cvtfield(self):
        self.assertEqual('xfoo', ndexloadbiogrid._cvtfield('xfoo'))
        self.assertEqual('x', ndexloadbiogrid._cvtfield('x'))
        self.assertEqual('', ndexloadbiogrid._cvtfield('-'))

    def test_update_or_upload_with_retry(self):
        temp_dir = tempfile.mkdtemp()
        try:
            p = MagicMock()
            p.datadir = os.path.join(temp_dir, 'datadir')
            p.profile = 'foo'
            p.organismloadplan = ndexloadbiogrid.get_organism_load_plan()
            p.chemicalloadplan = ndexloadbiogrid.get_chemical_load_plan()
            p.organismstyle = ndexloadbiogrid.get_organism_style()
            p.chemstyle = ndexloadbiogrid.get_chemical_style()
            p.biogridversion = '1.0.0'
            p.skipdownload = False
            loader = NdexBioGRIDLoader(p)
            loader._ndex = MagicMock()
            cxfile = os.path.join(temp_dir, 'file.cx')
            with open(cxfile, 'wb') as f:
                f.write(b'hello')
            loader._ndex.save_cx_stream_as_new_network = MagicMock(side_effect=Exception('error'))

            res = loader._update_or_upload_with_retry(cxfile=cxfile,
                                                      network_name='foo',
                                                      network_uuid=None,
                                                      maxretries=1,
                                                      retry_sleep=0)
            self.assertEqual(2, res)

            loader._ndex.update_cx_network = MagicMock(side_effect=Exception('error'))

            res = loader._update_or_upload_with_retry(cxfile=cxfile,
                                                      network_name='foo',
                                                      network_uuid='1234',
                                                      maxretries=1,
                                                      retry_sleep=0)
            self.assertEqual(2, res)

            loader._ndex.save_cx_stream_as_new_network = MagicMock(return_value={})

            res = loader._update_or_upload_with_retry(cxfile=cxfile,
                                                      network_name='foo',
                                                      maxretries=1,
                                                      retry_sleep=0)
            self.assertEqual(0, res)
        finally:
            shutil.rmtree(temp_dir)

    def test_apply_simple_spring_layout(self):
        net = NiceCXNetwork()
        n_one = net.create_node('node1')
        n_two = net.create_node('node2')
        net.create_edge(n_one, n_two, 'links')
        p = MagicMock()
        p.datadir = 'datadir'
        p.profile = 'foo'
        p.organismloadplan = ndexloadbiogrid.get_organism_load_plan()
        p.chemicalloadplan = ndexloadbiogrid.get_chemical_load_plan()
        p.organismstyle = ndexloadbiogrid.get_organism_style()
        p.chemstyle = ndexloadbiogrid.get_chemical_style()
        p.biogridversion = '1.0.0'
        p.skipdownload = False
        loader = NdexBioGRIDLoader(p)
        loader._apply_simple_spring_layout(net)

        aspect = net.get_opaque_aspect('cartesianLayout')
        self.assertEqual(2, len(aspect))

        # try with 19 nodes
        net = NiceCXNetwork()
        for x in range(0, 19):
            net.create_node(str(x))
        loader._apply_simple_spring_layout(net)

        aspect = net.get_opaque_aspect('cartesianLayout')
        self.assertEqual(19, len(aspect))

        # try with 99 nodes
        net = NiceCXNetwork()
        for x in range(0, 99):
            net.create_node(str(x))
        loader._apply_simple_spring_layout(net)

        aspect = net.get_opaque_aspect('cartesianLayout')
        self.assertEqual(99, len(aspect))

        # try with 101 nodes
        net = NiceCXNetwork()
        for x in range(0, 101):
            net.create_node(str(x))
        loader._apply_simple_spring_layout(net)

        aspect = net.get_opaque_aspect('cartesianLayout')
        self.assertEqual(101, len(aspect))

    def test_check_if_data_dir_exists(self):
        temp_dir = tempfile.mkdtemp()
        try:
            p = MagicMock()
            p.datadir = temp_dir
            p.profile = 'foo'
            p.organismloadplan = ndexloadbiogrid.get_organism_load_plan()
            p.chemicalloadplan = ndexloadbiogrid.get_chemical_load_plan()
            p.organismstyle = ndexloadbiogrid.get_organism_style()
            p.chemstyle = ndexloadbiogrid.get_chemical_style()
            p.biogridversion = '1.0.0'
            p.skipdownload = False
            loader = NdexBioGRIDLoader(p)
            self.assertTrue(loader._check_if_data_dir_exists())

            p.datadir = os.path.join(temp_dir, 'foo')
            loader = NdexBioGRIDLoader(p)
            self.assertFalse(loader._check_if_data_dir_exists())
        finally:
            shutil.rmtree(temp_dir)

    def test_write_nice_cx_to_file(self):
        temp_dir = tempfile.mkdtemp()
        try:
            p = MagicMock()
            p.datadir = temp_dir
            p.profile = 'foo'
            p.organismloadplan = ndexloadbiogrid.get_organism_load_plan()
            p.chemicalloadplan = ndexloadbiogrid.get_chemical_load_plan()
            p.organismstyle = ndexloadbiogrid.get_organism_style()
            p.chemstyle = ndexloadbiogrid.get_chemical_style()
            p.biogridversion = '1.0.0'
            p.skipdownload = False
            loader = NdexBioGRIDLoader(p)
            loader._network = NiceCXNetwork()
            loader._network.create_node('hi')
            loader._network.set_name('name')
            cxfile = os.path.join(temp_dir, 'some.cx')
            loader._write_nice_cx_to_file(cxfile)

            self.assertTrue(os.path.isfile(cxfile))

            checknet = ndex2.create_nice_cx_from_file(cxfile)
            self.assertEqual('name', checknet.get_name())

        finally:
            shutil.rmtree(temp_dir)


    @unittest.skip("skipping test_10")
    def test_10_using_panda_generate_organism_CX_and_upload(self):

        expected_organism_header = [
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

            status_code, biogrid_organism_file_path = self.NdexBioGRIDLoader._unzip_biogrid_file(file_name, 'organism')

            with self.subTest():
                self.assertEqual(status_code, 0, 'Unable to extract ' + file_name + ' from archive')

                header, status_code_1 = self.NdexBioGRIDLoader._get_header(biogrid_organism_file_path)
                self.assertEqual(status_code_1, 0, 'Unable to get header from ' + biogrid_organism_file_path)
                self.assertListEqual(expected_organism_header, header)

                biogrid_organism_CX_path, network_name   = \
                    self.NdexBioGRIDLoader._using_panda_generate_nice_cx(biogrid_organism_file_path, entry,
                                                                         self.__class__._organism_template, 'organism')

                self.assertIsNotNone(biogrid_organism_CX_path, 'No path for CX file generated from ' + file_name)

                #self.collapse_edges()

                status_code1 = self.NdexBioGRIDLoader._upload_cx(biogrid_organism_CX_path, network_name)
                self.assertEqual(status_code_1, 0, 'Unable to upload ' + network_name)



    @unittest.skip("skipping test_20")
    def test_20_using_panda_generate_chemical_CX_and_upload(self):

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


        for entry in self.chemicals_file_entries:

            file_name = self.NdexBioGRIDLoader._get_biogrid_chemicals_file_name(entry)

            status_code, biogrid_chemicals_file_path = self.NdexBioGRIDLoader._unzip_biogrid_file(file_name, 'chemicals')

            with self.subTest():
                self.assertEqual(status_code, 0, 'Unable to extract ' + file_name + ' from archive')

                header, status_code_1 = self.NdexBioGRIDLoader._get_header(biogrid_chemicals_file_path)
                self.assertEqual(status_code_1, 0, 'Unable to get header from ' + biogrid_chemicals_file_path)
                self.assertListEqual(expected_chemical_header, header)

                biogrid_chemical_CX_path, network_name  = \
                    self.NdexBioGRIDLoader._using_panda_generate_nice_cx(biogrid_chemicals_file_path, entry,
                                                                         self.__class__._chemical_template, 'chemical')

                self.assertEqual(status_code_1, 0, 'Unable to generate CX from ' + biogrid_chemicals_file_path)
                self.assertIsNotNone(biogrid_chemical_CX_path, 'No path for CX file generated from ' + file_name)

                status_code1 = self.NdexBioGRIDLoader._upload_cx(biogrid_chemical_CX_path, network_name)
                self.assertEqual(status_code_1, 0, 'Unable to upload ' + network_name)



    @unittest.skip("skipping test_30")
    def test_30_generate_organism_CX_and_upload(self):

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


                biogrid_organism_CX_path, network_name, status_code_1 = \
                    self.NdexBioGRIDLoader._generate_CX_from_biogrid_organism_file(biogrid_organism_file_path, entry, \
                                                                                   protein_template)
                self.assertEqual(status_code_1, 0, 'Unable to generate CX from ' + biogrid_organism_file_path)


                status_code1 = self.NdexBioGRIDLoader._upload_cx(biogrid_organism_CX_path, network_name)
                self.assertEqual(status_code_1, 0, 'Unable to upload ' + network_name)


