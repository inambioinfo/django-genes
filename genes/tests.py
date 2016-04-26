from django.test import TestCase
from django.core.exceptions import FieldError
from django.db import IntegrityError
from fixtureless import Factory

from organisms.models import Organism
from genes.models import Gene, CrossRef, CrossRefDB
from genes.utils import translate_genes

factory = Factory()


class TranslateTestCase(TestCase):
    def setUp(self):
        org = factory.create(Organism)
        xrdb1 = CrossRefDB(name="ASDF", url="http://www.example.com")
        xrdb1.save()
        xrdb2 = CrossRefDB(name="XRDB2", url="http://www.example.com/2")
        xrdb2.save()

        # g1 and g2 have both standard and systematic names.
        g1 = Gene(entrezid=1, systematic_name="g1", standard_name="G1",
                  description="asdf", organism=org, aliases="gee1 GEE1")
        g1.save()
        g2 = Gene(entrezid=2, systematic_name="g2", standard_name="G2",
                  description="asdf", organism=org, aliases="gee2 GEE2")
        g2.save()

        xref1 = CrossRef(crossrefdb=xrdb1, gene=g1, xrid="XRID1")
        xref1.save()
        xref2 = CrossRef(crossrefdb=xrdb2, gene=g2, xrid="XRID1")
        xref2.save()
        xref3 = CrossRef(crossrefdb=xrdb1, gene=g1, xrid="XRRID1")
        xref3.save()
        xref4 = CrossRef(crossrefdb=xrdb1, gene=g2, xrid="XRID2")
        xref4.save()

        org2 = Organism(taxonomy_id=1234, common_name="Computer mouse",
                        scientific_name="Mus computurus",
                        slug="mus-computurus")
        org2.save()
        org3 = Organism(taxonomy_id=4321, common_name="Computer screen",
                        scientific_name="Monitorus computurus",
                        slug="monitorus-computurus")
        org3.save()

        # Make systematic and standard name the same for the following genes,
        # but make organisms different. Skip entrezid 3 since that is used by
        # other tests.
        g4 = Gene(entrezid=4, systematic_name="acdc", standard_name="ACDC",
                  description="asdf", organism=org2, aliases="gee4 GEE4")
        g4.save()
        g5 = Gene(entrezid=5, systematic_name="acdc", standard_name="ACDC",
                  description="asdf", organism=org3, aliases="gee5 GEE5")
        g5.save()

        # g101 has standard name, but no systematic name.
        g101 = Gene(entrezid=101, standard_name="std_101", organism=org2)
        g101.save()

        # g102 has systematic name, but no standard name.
        g102 = Gene(entrezid=102, systematic_name="sys_102", organism=org2)
        g102.save()

        # g103 has neither standard name nor systematic name.
        g103 = Gene(entrezid=103, organism=org2)
        g103.save()

    def test_translate_symbol_entrez_diff_organisms(self):
        """
        translate_genes() should be able to differentiate between different
        organism genes when passed identical symbols.
        """
        # This test also confirmed that when both standard name and systematic
        # name are available, the sysmbol will be standard name.
        translation = translate_genes(id_list=['ACDC'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Mus computurus")
        self.assertEqual(translation, {'ACDC': [4], 'not_found': []})

    def test_translate_symbol_entrez_diff_organisms2(self):
        """
        Same as previous test, but uses the other organism as input.
        """
        translation = translate_genes(id_list=['ACDC'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Monitorus computurus")
        self.assertEqual(translation, {'ACDC': [5], 'not_found': []})

    def test_translate_entrez_entrez(self):
        """
        Test translation from entrez to entrez.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez", to_id="Entrez")
        self.assertEqual(translation, {1: [1, ], 2: [2, ], 'not_found': []})

    def test_translate_entrez_standard_name(self):
        """
        Test translation from entrez to standard names.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez",
                                      to_id="Standard name")
        self.assertEqual(translation,
                         {1: ['G1', ], 2: ['G2', ], 'not_found': []})

    def test_translate_entrez_systematic_name(self):
        """
        Test translation from entrez to systematic names.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez",
                                      to_id="Systematic name")
        self.assertEqual(translation,
                         {1: ['g1', ], 2: ['g2', ], 'not_found': []})

    def test_translate_entrez_xrdb(self):
        """
        Test translation from entrez to ASDF.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez", to_id="ASDF")
        self.assertEqual(translation, {1: ['XRID1', 'XRRID1', ],
                                       2: ['XRID2', ], 'not_found': []})

    def test_translate_xrdb_entrez(self):
        """
        Test translation from ASDF to entrez.
        """
        translation = translate_genes(id_list=['XRID1', 'XRRID1', 'XRID2'],
                                      from_id="ASDF", to_id="Entrez")
        self.assertEqual(translation, {'XRID1': [1, ], 'XRRID1': [1, ],
                                       'XRID2': [2, ], 'not_found': []})

    def test_translate_entrez_entrez_missing(self):
        """
        Test translation from entrez to entrez with a missing value.
        """
        translation = translate_genes(id_list=[1, 2, 3],
                                      from_id="Entrez", to_id="Entrez")
        self.assertEqual(translation, {1: [1, ], 2: [2, ], 'not_found': [3]})

    def test_translate_entrez_standard_name_missing(self):
        """
        Test translation from entrez to standard names with a missing value.
        """
        translation = translate_genes(id_list=[1, 2, 3],
                                      from_id="Entrez", to_id="Standard name")
        self.assertEqual(translation,
                         {1: ['G1', ], 2: ['G2', ], 'not_found': [3]})

    def test_translate_symbol_entrez(self):
        """
        Test translation from symbol to entrez when either standard name or
        systematic name is null.
        """
        # Test the gene that has standard name.
        translation = translate_genes(id_list=['std_101'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Mus computurus")
        self.assertEqual(translation, {'std_101': [101], 'not_found': []})
        # Test the gene that does NOT have standard name.
        translation = translate_genes(id_list=['sys_102'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Mus computurus")
        self.assertEqual(translation, {'sys_102': [102], 'not_found': []})
        # Test the gene that has neither standard name nor systematic name.
        translation = translate_genes(id_list=[''],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Mus computurus")
        self.assertEqual(translation, {'': [103], 'not_found': []})

    def test_translate_entrez_symbol(self):
        """
        Test translation from entrez to symbol when either standard name or
        systematic name is null.
        """
        # Test the gene that has standard name.
        translation = translate_genes(id_list=[101],
                                      from_id="Entrez", to_id="Symbol",
                                      organism="Mus computurus")
        self.assertEqual(translation, {101: ['std_101'], 'not_found': []})
        # Test the gene that does NOT have standard name.
        translation = translate_genes(id_list=[102],
                                      from_id="Entrez", to_id="Symbol",
                                      organism="Mus computurus")
        self.assertEqual(translation, {102: ['sys_102'], 'not_found': []})
        # Test the gene that has neither standard name nor systematic name.
        translation = translate_genes(id_list=[103],
                                      from_id="Entrez", to_id="Symbol",
                                      organism="Mus computurus")
        self.assertEqual(translation, {103: [''], 'not_found': []})

    def tearDown(self):
        Organism.objects.all().delete()    # Remove Organism objects.
        Gene.objects.all().delete()        # Remove Gene objects.
        CrossRef.objects.all().delete()    # Remove CrossRef objects.
        CrossRefDB.objects.all().delete()  # Remove CrossRefDB objects.


class CrossRefDBTestCase(TestCase):
    def test_saving_xrdb(self):
        """
        Test that this simple CrossRefDB creation raises no errors.
        """
        factory.create(CrossRefDB, {"name": "XRDB1"})

    def test_saving_xrdb_no_name(self):
        """
        Check that CrossRefDBs in database are required to have a non-null
        name - if they do, raise IntegrityError.
        """
        with self.assertRaises(IntegrityError):
            factory.create(CrossRefDB, {"name": None})

    def test_saving_xrdb_blank_name(self):
        """
        Check that CrossRefDBs in database are required to have a name that
        is not an empty string - if they do, raise FieldError.
        """
        with self.assertRaises(FieldError):
            factory.create(CrossRefDB, {"name": ""})
