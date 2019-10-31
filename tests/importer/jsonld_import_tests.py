

import os
import json
import csv
import base64
from io import BytesIO
from tests import test_settings
from operator import itemgetter
from django.core import management
from django.test.client import RequestFactory, Client
from django.contrib.auth.models import User, Group, AnonymousUser
from django.urls import reverse
from django.db import connection
from tests.base_test import ArchesTestCase
from arches.app.utils.skos import SKOSReader
from arches.app.models.models import TileModel, ResourceInstance
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.data_management.resources.importer import BusinessDataImporter
from arches.app.utils.data_management.resources.exporter import ResourceExporter as BusinessDataExporter
from arches.app.utils.data_management.resource_graphs.importer import import_graph as ResourceGraphImporter


# these tests can be run from the command line via
# python manage.py test tests/importer/jsonld_import_tests.py --settings="tests.test_settings"


class JsonLDExportTests(ArchesTestCase):
    @classmethod
    def setUpClass(cls):
        # This runs once per instantiation
        cls.loadOntology()
        cls.factory = RequestFactory()

        sql = """
            INSERT INTO public.oauth2_provider_application(
                id,client_id, redirect_uris, client_type, authorization_grant_type,
                client_secret,
                name, user_id, skip_authorization, created, updated)
            VALUES (
                44,'{oauth_client_id}', 'http://localhost:8000/test', 'public', 'client-credentials',
                '{oauth_client_secret}',
                'TEST APP', {user_id}, false, '1-1-2000', '1-1-2000');
            INSERT INTO public.oauth2_provider_accesstoken(
                token, expires, scope, application_id, user_id, created, updated)
                VALUES ('{token}', '1-1-2068', 'read write', 44, {user_id}, '1-1-2018', '1-1-2018');
        """

        cls.token = 'abc'
        cls.oauth_client_id = 'AAac4uRQSqybRiO6hu7sHT50C4wmDp9fAmsPlCj9'
        cls.oauth_client_secret = '7fos0s7qIhFqUmalDI1QiiYj0rAtEdVMY4hYQDQjOxltbRCBW3dIydOeMD4MytDM9ogCPiYFiMBW6o6ye5bMh5dkeU7pg1cH86wF6Bap9Ke2aaAZaeMPejzafPSj96ID'

        sql = sql.format(
            token=cls.token,
            user_id=1,  # admin is 1
            oauth_client_id=cls.oauth_client_id,
            oauth_client_secret=cls.oauth_client_secret
        )

        cursor = connection.cursor()
        cursor.execute(sql)

        key = '{0}:{1}'.format(cls.oauth_client_id, cls.oauth_client_secret)
        cls.client = Client(HTTP_AUTHORIZATION='Bearer %s' % cls.token)

        skos = SKOSReader()
        rdf = skos.read_file('tests/fixtures/jsonld_base/rdm/jsonld_test_thesaurus.xml')
        ret = skos.save_concepts_from_skos(rdf)

        skos = SKOSReader()
        rdf = skos.read_file('tests/fixtures/jsonld_base/rdm/jsonld_test_collections.xml')
        ret = skos.save_concepts_from_skos(rdf)

        # Load up the models and data only once
        with open(os.path.join('tests/fixtures/jsonld_base/models/test_1_basic_object.json'), 'rU') as f:
            archesfile = JSONDeserializer().deserialize(f)
        ResourceGraphImporter(archesfile['graph'])

        with open(os.path.join('tests/fixtures/jsonld_base/models/test_2_complex_object.json'), 'rU') as f:
            archesfile2 = JSONDeserializer().deserialize(f)
        ResourceGraphImporter(archesfile2['graph'])

        skos = SKOSReader()
        rdf = skos.read_file('tests/fixtures/jsonld_base/rdm/5098-thesaurus.xml')
        ret = skos.save_concepts_from_skos(rdf)

        skos = SKOSReader()
        rdf = skos.read_file('tests/fixtures/jsonld_base/rdm/5098-collections.xml')
        ret = skos.save_concepts_from_skos(rdf)

        # Load up the models and data only once
        with open(os.path.join('tests/fixtures/jsonld_base/models/5098_concept_list.json'), 'rU') as f:
            archesfile = JSONDeserializer().deserialize(f)
        ResourceGraphImporter(archesfile['graph'])

    def setUp(self):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def tearDown(self):
        pass

    def test_1_basic_import(self):
        data = """{
            "@id": "http://localhost:8000/resources/221d1154-fa8e-11e9-9cbb-3af9d3b32b71",
            "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object",
            "http://www.cidoc-crm.org/cidoc-crm/P3_has_note": "test!"
            }"""

        url = reverse('resources_graphid', kwargs={"graphid": "bf734b4e-f6b5-11e9-8f09-a4d18cec433a", "resourceid": "221d1154-fa8e-11e9-9cbb-3af9d3b32b71"})
        response = self.client.put(url, data=data, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 201)
        js = response.json()
        if type(js) == list:
            js = js[0]

        self.assertTrue('@id' in js)
        self.assertTrue(js['@id'] == "http://localhost:8000/resources/221d1154-fa8e-11e9-9cbb-3af9d3b32b71")
        self.assertTrue('http://www.cidoc-crm.org/cidoc-crm/P3_has_note' in js)
        self.assertTrue(js['http://www.cidoc-crm.org/cidoc-crm/P3_has_note'] == 'test!')

    def test_2_complex_import_data(self):

        data = """
            {
                "@id": "http://localhost:8000/resources/12345678-abcd-11e9-9cbb-3af9d3b32b71",
                "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object",
                "http://www.cidoc-crm.org/cidoc-crm/P101_had_as_general_use": {
                    "@id": "http://localhost:8000/concepts/fb457e76-e018-41e7-9be3-0f986816450a",
                    "@type": "http://www.cidoc-crm.org/cidoc-crm/E55_Type",
                    "http://www.cidoc-crm.org/cidoc-crm/P2_has_type": {
                        "@id": "http://localhost:8000/concepts/14c92c17-5e2f-413a-95c2-3c5e41ee87d2",
                        "@type": "http://www.cidoc-crm.org/cidoc-crm/E55_Type",
                        "http://www.w3.org/2000/01/rdf-schema#label": "Meta Type A"
                    },
                    "http://www.w3.org/2000/01/rdf-schema#label": "Test Type A"
                },
                "http://www.cidoc-crm.org/cidoc-crm/P160_has_temporal_projection": {
                    "@id": "http://localhost:8000/tile/9c1ec6b9-1094-427f-acf6-e9c3fca643b6/node/127193ea-fa6d-11e9-b369-3af9d3b32b71",
                    "@type": "http://www.cidoc-crm.org/cidoc-crm/E52_Time-Span",
                    "http://www.cidoc-crm.org/cidoc-crm/P79_beginning_is_qualified_by": "example",
                    "http://www.cidoc-crm.org/cidoc-crm/P82a_begin_of_the_begin": {
                        "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                        "@value": "2019-10-01"
                    }
                },
                "http://www.cidoc-crm.org/cidoc-crm/P2_has_type": {
                    "@id": "http://localhost:8000/concepts/6bac5802-a6f8-427c-ba5f-d4b30d5b070e",
                    "@type": "http://www.cidoc-crm.org/cidoc-crm/E55_Type",
                    "http://www.w3.org/2000/01/rdf-schema#label": "Single Type A"
                },
                "http://www.cidoc-crm.org/cidoc-crm/P3_has_note": "Test Data",
                "http://www.cidoc-crm.org/cidoc-crm/P45_consists_of": [
                    {
                        "@id": "http://localhost:8000/concepts/9b61c995-71d8-4bce-987b-0ffa3da4c71c",
                        "@type": "http://www.cidoc-crm.org/cidoc-crm/E57_Material",
                        "http://www.w3.org/2000/01/rdf-schema#label": "material b"
                    },
                    {
                        "@id": "http://localhost:8000/concepts/36c8d7a3-32e7-49e4-bd4c-2169a06b240a",
                        "@type": "http://www.cidoc-crm.org/cidoc-crm/E57_Material",
                        "http://www.w3.org/2000/01/rdf-schema#label": "material a"
                    }
                ],
                "http://www.cidoc-crm.org/cidoc-crm/P57_has_number_of_parts": 12
            }
        """

        url = reverse('resources_graphid', kwargs={"graphid": "ee72fb1e-fa6c-11e9-b369-3af9d3b32b71", "resourceid": "12345678-abcd-11e9-9cbb-3af9d3b32b71"})
        response = self.client.put(url, data=data, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 201)
        js = response.json()
        if type(js) == list:
            js = js[0]

        self.assertTrue('@id' in js)
        self.assertTrue(js['@id'] == "http://localhost:8000/resources/12345678-abcd-11e9-9cbb-3af9d3b32b71")

    def test_3_5098_concepts(self):
        data = """
            {
                "@id": "http://localhost:8000/resources/0b4439a8-beca-11e9-b4dc-0242ac160002",
                "@type": "http://www.cidoc-crm.org/cidoc-crm/E21_Person",
                "http://www.cidoc-crm.org/cidoc-crm/P67i_is_referred_to_by": {
                    "@id": "http://localhost:8000/tile/cad329aa-1802-416e-bbce-5f71e21b1a47/node/accb030c-bec9-11e9-b4dc-0242ac160002",
                    "@type": "http://www.cidoc-crm.org/cidoc-crm/E33_Linguistic_Object",
                    "http://www.cidoc-crm.org/cidoc-crm/P2_has_type": [
                        {
                            "@id": "http://localhost:8000/concepts/c3c4b8a8-39bb-41e7-af45-3a0c60fa4ddf",
                            "@type": "http://www.cidoc-crm.org/cidoc-crm/E55_Type",
                            "http://www.w3.org/2000/01/rdf-schema#label": "Concept 2"
                        },
                        {
                            "@id": "http://localhost:8000/concepts/0bb450bc-8fe3-46cb-968e-2b56849e6e96",
                            "@type": "http://www.cidoc-crm.org/cidoc-crm/E55_Type",
                            "http://www.w3.org/2000/01/rdf-schema#label": "Concept 1"
                        }
                    ]
                }
            }
        """

        url = reverse('resources_graphid', kwargs={"graphid": "92ccf5aa-bec9-11e9-bd39-0242ac160002", "resourceid": '0b4439a8-beca-11e9-b4dc-0242ac160002'})
        response = self.client.put(url, data=data, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 201)
        js = response.json()
        if type(js) == list:
            js = js[0]

        self.assertTrue('@id' in js)
        self.assertTrue(js['@id'] == "http://localhost:8000/resources/0b4439a8-beca-11e9-b4dc-0242ac160002")

        print(f"Got JSON for test 3: {js}")
        types = js["http://www.cidoc-crm.org/cidoc-crm/P67i_is_referred_to_by"]["http://www.cidoc-crm.org/cidoc-crm/P2_has_type"]   
        self.assertTrue(type(types) == list)
        self.assertTrue(len(types) == 2)
        cids = ["http://localhost:8000/concepts/c3c4b8a8-39bb-41e7-af45-3a0c60fa4ddf", "http://localhost:8000/concepts/0bb450bc-8fe3-46cb-968e-2b56849e6e96"]
        self.assertTrue(types[0]['@id'] in cids)
        self.assertTrue(types[1]['@id'] in cids)
        self.assertTrue(types[0]['@id'] != types[1]['@id'])

    def test_4_5098_resinst(self):
        data = """
            {
                "@id": "http://localhost:8000/resources/abcd1234-1234-1129-b6e7-3af9d3b32b71",
                "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object",
                "http://www.cidoc-crm.org/cidoc-crm/P130_shows_features_of": [
                    {
                        "@id": "http://localhost:8000/resources/12bbf5bc-fa85-11e9-91b8-3af9d3b32b71",
                        "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object"
                    },
                    {
                        "@id": "http://localhost:8000/resources/24d0d25a-fa75-11e9-b369-3af9d3b32b71",
                        "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object"
                    }
                ],
                "http://www.cidoc-crm.org/cidoc-crm/P3_has_note": "res inst list import"
            }
        """

        # Make instances for this new one to reference
        BusinessDataImporter('tests/fixtures/jsonld_base/data/test_2_instances.json').import_business_data()  

        url = reverse('resources_graphid', kwargs={"graphid": "ee72fb1e-fa6c-11e9-b369-3af9d3b32b71", "resourceid": "abcd1234-1234-1129-b6e7-3af9d3b32b71"})
        response = self.client.put(url, data=data, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 201)
        js = response.json()
        if type(js) == list:
            js = js[0]        

        print(f"Got json for test 4: {js}")
        self.assertTrue('@id' in js)
        self.assertTrue(js['@id'] == 'http://localhost:8000/resources/abcd1234-1234-1129-b6e7-3af9d3b32b71')
        self.assertTrue("http://www.cidoc-crm.org/cidoc-crm/P130_shows_features_of" in js)
        feats = js["http://www.cidoc-crm.org/cidoc-crm/P130_shows_features_of"]
        self.assertTrue(type(feats) == list)
        self.assertTrue(len(feats) == 2)
        rids = ["http://localhost:8000/resources/12bbf5bc-fa85-11e9-91b8-3af9d3b32b71", "http://localhost:8000/resources/24d0d25a-fa75-11e9-b369-3af9d3b32b71"]
        self.assertTrue(feats[0]['@id'] in rids)
        self.assertTrue(feats[1]['@id'] in rids)

    def test_5_5098_resinst_branch(self):
        BusinessDataImporter('tests/fixtures/jsonld_base/data/test_2_instances.json').import_business_data()  

        data = """
            {
                "@id": "http://localhost:8000/resources/7fffffff-faa1-11e9-84de-3af9d3b32b71",
                "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object",
                "http://www.cidoc-crm.org/cidoc-crm/P67i_is_referred_to_by": {
                    "@id": "http://localhost:8000/tile/a4896405-5c73-49f4-abd3-651911e82fde/node/51c3ede8-faa1-11e9-84de-3af9d3b32b71",
                    "@type": "http://www.cidoc-crm.org/cidoc-crm/E33_Linguistic_Object",
                    "http://www.cidoc-crm.org/cidoc-crm/P128i_is_carried_by": [
                        {
                            "@id": "http://localhost:8000/resources/24d0d25a-fa75-11e9-b369-3af9d3b32b71",
                            "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object"
                        },
                        {
                            "@id": "http://localhost:8000/resources/12bbf5bc-fa85-11e9-91b8-3af9d3b32b71",
                            "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object"
                        }
                    ]
                }
            }
        """

        # Load up the models and data only once
        with open(os.path.join('tests/fixtures/jsonld_base/models/5098_b_resinst.json'), 'rU') as f:
            archesfile = JSONDeserializer().deserialize(f)
        ResourceGraphImporter(archesfile['graph'])

        url = reverse('resources_graphid', kwargs={"graphid": "40dbcffa-faa1-11e9-84de-3af9d3b32b71", "resourceid": "7fffffff-faa1-11e9-84de-3af9d3b32b71"})
        response = self.client.put(url, data=data, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 201)
        js = response.json()
        if type(js) == list:
            js = js[0]

        print(f"Got json for test 5: {js}")
        self.assertTrue('@id' in js)
        self.assertTrue(js['@id'] == 'http://localhost:8000/resources/7fffffff-faa1-11e9-84de-3af9d3b32b71')
        self.assertTrue("http://www.cidoc-crm.org/cidoc-crm/P67i_is_referred_to_by" in js)
        feats = js["http://www.cidoc-crm.org/cidoc-crm/P67i_is_referred_to_by"]["http://www.cidoc-crm.org/cidoc-crm/P128i_is_carried_by"]
        self.assertTrue(type(feats) == list)
        self.assertTrue(len(feats) == 2)

    def test_6_5126_collection_filter(self):

        skos = SKOSReader()
        rdf = skos.read_file('tests/fixtures/jsonld_base/rdm/5126-thesaurus.xml')
        ret = skos.save_concepts_from_skos(rdf)

        skos = SKOSReader()
        rdf = skos.read_file('tests/fixtures/jsonld_base/rdm/5126-collections.xml')
        ret = skos.save_concepts_from_skos(rdf)

        # Load up the models and data only once
        with open(os.path.join('tests/fixtures/jsonld_base/models/5126_collection_ambiguity.json'), 'rU') as f:
            archesfile = JSONDeserializer().deserialize(f)
        ResourceGraphImporter(archesfile['graph'])

        data = """
            {
                "@id": "http://localhost:8000/resources/69a4af50-c055-11e9-b4dc-0242ac160002",
                "@type": "http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object",
                "http://www.cidoc-crm.org/cidoc-crm/P2_has_type": {
                    "@id": "http://vocab.getty.edu/aat/300404216",
                    "@type": "http://www.cidoc-crm.org/cidoc-crm/E55_Type",
                    "http://www.w3.org/2000/01/rdf-schema#label": "aquarelles (paintings)"
                }
            }
        """
        url = reverse('resources_graphid', kwargs={"graphid": "09e3dc8a-c055-11e9-b4dc-0242ac160002", "resourceid": "69a4af50-c055-11e9-b4dc-0242ac160002"})
        response = self.client.put(url, data=data, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(response.status_code, 201)
        js = response.json()
        if type(js) == list:
            js = js[0]

        print(f"Got JSON for test 5: {js}")
        self.assertTrue('@id' in js)
        self.assertTrue(js['@id'] == 'http://localhost:8000/resources/69a4af50-c055-11e9-b4dc-0242ac160002')
