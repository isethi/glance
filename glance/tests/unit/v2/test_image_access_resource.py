# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

import webob

import glance.api.v2.image_access
from glance.common import exception
from glance.common import utils
import glance.schema
import glance.tests.unit.utils as unit_test_utils
import glance.tests.utils as test_utils


UUID3 = 'd80a1a6c-bd1f-41c5-90ee-81afedb1d58d'
UUID4 = 'b85abd86-55b3-4d5b-b0b4-5d0a6e6042fc'

TENANT3 = '7838eb7b-6ded-434a-882c-b344c77fe8df'
TENANT4 = '3c014f32-55eb-467d-8fcb-4bd706012f81'
TENANT5 = '6a3e60e8-cfa9-4a9e-a90a-62b42cea92b8'


class TestImageAccessController(test_utils.BaseTestCase):

    def setUp(self):
        super(TestImageAccessController, self).setUp()
        self.db = unit_test_utils.FakeDB()
        self._create_images()
        self.controller = glance.api.v2.image_access.Controller(self.db)

    def _create_images(self):
        self.members = [
            {
                'image_id': UUID3,
                'member': TENANT3,
                'can_share': True,
                'id': 1
            },
            {
                'image_id': UUID4,
                'member': TENANT4,
                'can_share': True,
                'id': 2
            },
            {
                'image_id': UUID3,
                'member': TENANT5,
                'can_share': True,
                'id': 3
            },
            {
                'image_id': UUID3,
                'member': TENANT4,
                'can_share': False,
                'id': 4
            },
        ]
        [self.db.image_member_create(None, member) for member in self.members]

    def test_index(self):
        req = unit_test_utils.get_fake_request()
        output = self.controller.index(req, UUID3)
        self.maxDiff = None
        expected = {
            'access_records': [
                {
                    'image_id': UUID3,
                    'member': TENANT4,
                    'can_share': False,
                    'id': 4,
                    'deleted': False
                },
                {
                    'image_id': UUID3,
                    'member': TENANT5,
                    'can_share': True,
                    'id': 3,
                    'deleted': False
                },
                {
                    'image_id': UUID3,
                    'member': TENANT3,
                    'can_share': True,
                    'id': 1,
                    'deleted': False
                },
            ],
            'image_id': unit_test_utils.UUID1,
        }
        del output['access_records'][0]['created_at']
        del output['access_records'][1]['created_at']
        del output['access_records'][2]['created_at']
        print "length\n"
        print len(output)
        print "\noutput\n"
        print output
        self.assertEqual(expected, output)

    def test_index_return_parameters(self):
        image_id = unit_test_utils.UUID1
        self.config(limit_param_default=1, api_limit_max=3)
        request = unit_test_utils.get_fake_request()
        output = self.controller.index(request, image_id, marker=2, limit=1,
                                       sort_key='created_at', sort_dir='desc')
        self.assertEqual(1, len(output['images']))
        actual = set([image['id'] for image in output['images']])
        expected = set([UUID2])
        self.assertEqual(actual, expected)
        self.assertEqual(UUID2, output['next_marker'])

    def test_index_next_marker(self):
        self.config(limit_param_default=1, api_limit_max=3)
        request = unit_test_utils.get_fake_request()
        output = self.controller.index(request, marker=UUID4, limit=2)
        self.assertEqual(2, len(output['images']))
        actual = set([image['id'] for image in output['images']])
        expected = set([UUID3, UUID2])
        self.assertEqual(actual, expected)
        self.assertEqual(UUID2, output['next_marker'])

    def test_index_no_next_marker(self):
        self.config(limit_param_default=1, api_limit_max=3)
        request = unit_test_utils.get_fake_request()
        output = self.controller.index(request, marker=UUID1, limit=2)
        self.assertEqual(0, len(output['images']))
        actual = set([image['id'] for image in output['images']])
        expected = set([])
        self.assertEqual(actual, expected)
        self.assertTrue('next_marker' not in output)

    def test_index_with_marker(self):
        self.config(limit_param_default=1, api_limit_max=3)
        path = '/images'
        request = unit_test_utils.get_fake_request(path)
        output = self.controller.index(request, marker=UUID3)
        actual = set([image['id'] for image in output['images']])
        self.assertEquals(1, len(actual))
        self.assertTrue(UUID2 in actual)

    def test_index_with_limit(self):
        path = '/images'
        limit = 2
        request = unit_test_utils.get_fake_request(path)
        output = self.controller.index(request, limit=limit)
        actual = set([image['id'] for image in output['images']])
        self.assertEquals(limit, len(actual))
        self.assertTrue(UUID4 in actual)
        self.assertTrue(UUID3 in actual)

    def test_index_greater_than_limit_max(self):
        self.config(limit_param_default=1, api_limit_max=3)
        path = '/images'
        request = unit_test_utils.get_fake_request(path)
        output = self.controller.index(request, limit=4)
        actual = set([image['id'] for image in output['images']])
        self.assertEquals(3, len(actual))
        self.assertTrue(output['next_marker'] not in output)

    def test_index_default_limit(self):
        self.config(limit_param_default=1, api_limit_max=3)
        path = '/images'
        request = unit_test_utils.get_fake_request(path)
        output = self.controller.index(request)
        actual = set([image['id'] for image in output['images']])
        self.assertEquals(1, len(actual))

    def test_index_with_sort_dir(self):
        path = '/images'
        request = unit_test_utils.get_fake_request(path)
        output = self.controller.index(request, sort_dir='asc', limit=3)
        actual = [image['id'] for image in output['images']]
        self.assertEquals(3, len(actual))
        self.assertEquals(UUID1, actual[0])
        self.assertEquals(UUID2, actual[1])
        self.assertEquals(UUID3, actual[2])

    def test_index_with_sort_key(self):
        path = '/images'
        request = unit_test_utils.get_fake_request(path)
        output = self.controller.index(request, sort_key='id', limit=3)
        actual = [image['id'] for image in output['images']]
        self.assertEquals(3, len(actual))
        self.assertEquals(UUID1, actual[0])
        self.assertEquals(UUID2, actual[1])
        self.assertEquals(UUID3, actual[2])

    def test_index_with_marker_not_found(self):
        fake_uuid = utils.generate_uuid()
        path = '/images'
        request = unit_test_utils.get_fake_request(path)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.index, request, marker=fake_uuid)

    def test_index_invalid_sort_key(self):
        path = '/images'
        request = unit_test_utils.get_fake_request(path)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.index, request, sort_key='foo')

    def test_index_zero_records(self):
        req = unit_test_utils.get_fake_request()
        output = self.controller.index(req, unit_test_utils.UUID2)
        expected = {
            'access_records': [],
            'image_id': unit_test_utils.UUID2,
        }
        self.assertEqual(expected, output)

    def test_index_nonexistant_image(self):
        req = unit_test_utils.get_fake_request()
        image_id = utils.generate_uuid()
        self.assertRaises(exception.NotFound,
                          self.controller.index, req, image_id)

    def test_show(self):
        req = unit_test_utils.get_fake_request()
        image_id = unit_test_utils.UUID1
        tenant_id = unit_test_utils.TENANT1
        output = self.controller.show(req, image_id, tenant_id)
        expected = {
            'id': 1,
            'image_id': image_id,
            'member': tenant_id,
            'can_share': True,
            'deleted': False,
        }
        del output['created_at']
        self.assertEqual(expected, output)

    def test_show_nonexistant_image(self):
        req = unit_test_utils.get_fake_request()
        image_id = utils.generate_uuid()
        tenant_id = unit_test_utils.TENANT1
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.show, req, image_id, tenant_id)

    def test_show_nonexistant_tenant(self):
        req = unit_test_utils.get_fake_request()
        image_id = unit_test_utils.UUID1
        tenant_id = utils.generate_uuid()
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.show, req, image_id, tenant_id)

    def test_create(self):
        member = utils.generate_uuid()
        fixture = {
            'member': member,
            'can_share': True,
            'id': 1,
        }
        req = unit_test_utils.get_fake_request()
        output = self.controller.create(req, unit_test_utils.UUID1, fixture)
        expected = {
            'image_id': unit_test_utils.UUID1,
            'id': 1 ,
            'member': member,
            'can_share': True,
            'deleted': False,
        }
        del output['created_at']
        self.assertEqual(output, expected) 


class TestImageAccessDeserializer(test_utils.BaseTestCase):

    def setUp(self):
        super(TestImageAccessDeserializer, self).setUp()
        self.deserializer = glance.api.v2.image_access.RequestDeserializer()

    def test_create(self):
        fixture = {
            'tenant_id': unit_test_utils.TENANT1,
            'can_share': False,
        }
        expected = {
            'access_record': {
                'member': unit_test_utils.TENANT1,
                'can_share': False,
            },
        }
        request = unit_test_utils.get_fake_request()
        request.body = json.dumps(fixture)
        output = self.deserializer.create(request)
        self.assertEqual(expected, output)

    def test_index(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?limit=1&marker=2' % image_id
        request = unit_test_utils.get_fake_request(path=path)
        output = self.deserializer.index(request, image_id)
        expected = {'image_id': image_id,
                    'limit': 1,
                    'marker': 2,
                    'sort_key': 'created_at',
                    'sort_dir': 'desc'}
        self.assertEqual(output, expected)
        
    def test_index_non_integer_limit(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?limit=blah' % image_id 
        request = unit_test_utils.get_fake_request(path)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.deserializer.index, request, image_id)

    def test_index_zero_limit(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?limit=0' % image_id 
        request = unit_test_utils.get_fake_request(path)
        expected = {'image_id': image_id,
                    'limit': 0,
                    'sort_key': 'created_at',
                    'sort_dir': 'desc'}
        output = self.deserializer.index(request, image_id)
        self.assertEqual(expected, output)

    def test_index_negative_limit(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?limit=-1' % image_id 
        request = unit_test_utils.get_fake_request(path)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.deserializer.index, request, image_id)

    def test_index_fraction(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?limit=.1' % image_id 
        request = unit_test_utils.get_fake_request(path)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.deserializer.index, request, image_id)

    def test_index_marker(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?marker=1' % image_id
        request = unit_test_utils.get_fake_request(path)
        output = self.deserializer.index(request, image_id)
        self.assertEqual(output.get('marker'), 1)

    def test_index_marker_not_specified(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access' % image_id
        request = unit_test_utils.get_fake_request(path)
        output = self.deserializer.index(request, image_id)
        self.assertFalse('marker' in output)

    def test_index_limit_not_specified(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access' % image_id
        request = unit_test_utils.get_fake_request(path)
        output = self.deserializer.index(request, image_id)
        self.assertFalse('limit' in output)

    def test_index_sort_key_id(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?sort_key=id' % image_id
        request = unit_test_utils.get_fake_request(path)
        output = self.deserializer.index(request, image_id)
        expected = {'image_id': image_id,'sort_key': 'id', 'sort_dir': 'desc'}
        self.assertEqual(output, expected)

    def test_index_sort_dir_asc(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?sort_dir=asc' % image_id
        request = unit_test_utils.get_fake_request(path)
        output = self.deserializer.index(request, image_id)
        expected = {'image_id': image_id, 
                    'sort_key': 'created_at', 
                    'sort_dir': 'asc'}
        self.assertEqual(output, expected)

    def test_index_sort_dir_bad_value(self):
        image_id = unit_test_utils.UUID1
        path = '/images/%s/access?sort_dir=blah' % image_id
        request = unit_test_utils.get_fake_request(path)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.deserializer.index, request, image_id)

class TestImageAccessSerializer(test_utils.BaseTestCase):
    serializer = glance.api.v2.image_access.ResponseSerializer()

    def test_show(self):
        fixture = {
            'image_id': unit_test_utils.UUID1,
            'member': unit_test_utils.TENANT1,
            'can_share': False,
        }
        self_href = ('/v2/images/%s/access/%s' %
                (unit_test_utils.UUID1, unit_test_utils.TENANT1))
        expected = {
            'access_record': {
                'tenant_id': unit_test_utils.TENANT1,
                'can_share': False,
                'self': self_href,
                'schema': '/v2/schemas/image/access',
                'image': '/v2/images/%s' % unit_test_utils.UUID1,
            },
        }
        response = webob.Response()
        self.serializer.show(response, fixture)
        self.assertEqual(expected, json.loads(response.body))

    def test_index(self):
        fixtures = [
            {
                'image_id': unit_test_utils.UUID1,
                'member': unit_test_utils.TENANT1,
                'can_share': False,
            },
            {
                'image_id': unit_test_utils.UUID1,
                'member': unit_test_utils.TENANT2,
                'can_share': True,
            },
        ]
        result = {
            'access_records': fixtures,
            'image_id': unit_test_utils.UUID1,
        }
        expected = {
            'access_records': [
                {
                    'tenant_id': unit_test_utils.TENANT1,
                    'can_share': False,
                    'self': ('/v2/images/%s/access/%s' %
                                    (unit_test_utils.UUID1,
                                     unit_test_utils.TENANT1)),
                    'schema': '/v2/schemas/image/access',
                    'image': '/v2/images/%s' % unit_test_utils.UUID1,
                },
                {
                    'tenant_id': unit_test_utils.TENANT2,
                    'can_share': True,
                    'self': ('/v2/images/%s/access/%s' %
                                    (unit_test_utils.UUID1,
                                     unit_test_utils.TENANT2)),
                    'schema': '/v2/schemas/image/access',
                    'image': '/v2/images/%s' % unit_test_utils.UUID1,
                },
            ],
           'first': '/v2/images/%s/access' % unit_test_utils.UUID1,
           'schema': '/v2/schemas/image/accesses',

        }
        response = webob.Response()
        self.serializer.index(response, result)
        self.assertEqual(expected, json.loads(response.body))

    def test_index_zero_access_records(self):
        result = {
            'access_records': [],
            'image_id': unit_test_utils.UUID1,
        }
        response = webob.Response()
        self.serializer.index(response, result)
        first_link = '/v2/images/%s/access' % unit_test_utils.UUID1
        expected = {
            'access_records': [],
            'first': first_link,
            'schema': '/v2/schemas/image/accesses',
        }
        self.assertEqual(expected, json.loads(response.body))

    def test_create(self):
        fixture = {
            'image_id': unit_test_utils.UUID1,
            'member': unit_test_utils.TENANT1,
            'can_share': False,
        }
        self_href = ('/v2/images/%s/access/%s' %
                (unit_test_utils.UUID1, unit_test_utils.TENANT1))
        expected = {
            'access': {
                'tenant_id': unit_test_utils.TENANT1,
                'can_share': False,
                'self': self_href,
                'schema': '/v2/schemas/image/access',
                'image': '/v2/images/%s' % unit_test_utils.UUID1,
            },
        }
        response = webob.Response()
        self.serializer.create(response, fixture)
        self.assertEqual(expected, json.loads(response.body))
        self.assertEqual(self_href, response.location)
