# Copyright 2013 OpenStack LLC.
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

import datetime

import webob

import glance.api.v2.image_members
from glance.openstack.common import cfg
from glance.openstack.common import uuidutils
from glance.tests.unit import base
import glance.tests.unit.utils as unit_test_utils
import glance.tests.utils as test_utils


DATETIME = datetime.datetime(2012, 5, 16, 15, 27, 36, 325355)
ISOTIME = '2012-05-16T15:27:36Z'


CONF = cfg.CONF

BASE_URI = unit_test_utils.BASE_URI


UUID1 = 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d'
UUID2 = 'a85abd86-55b3-4d5b-b0b4-5d0a6e6042fc'
UUID3 = '971ec09a-8067-4bc8-a91f-ae3557f1c4c7'
UUID4 = '6bbe7cc2-eae7-4c0f-b50d-a7160b0c6a86'

TENANT1 = '6838eb7b-6ded-434a-882c-b344c77fe8df'
TENANT2 = '2c014f32-55eb-467d-8fcb-4bd706012f81'
TENANT3 = '5a3e60e8-cfa9-4a9e-a90a-62b42cea92b8'
TENANT4 = 'c6c87f25-8a94-47ed-8c83-053c25f42df4'


def _db_fixture(id, **kwargs):
    obj = {
        'id': id,
        'name': None,
        'is_public': False,
        'properties': {},
        'checksum': None,
        'owner': None,
        'status': 'queued',
        'tags': [],
        'size': None,
        'location': None,
        'protected': False,
        'disk_format': None,
        'container_format': None,
        'deleted': False,
        'min_ram': None,
        'min_disk': None,
    }
    obj.update(kwargs)
    return obj


def _db_image_member_fixture(image_id, member_id, **kwargs):
    obj = {
        'image_id': image_id,
        'member': member_id,
    }
    obj.update(kwargs)
    return obj


class TestImageMembersController(test_utils.BaseTestCase):

    def setUp(self):
        super(TestImageMembersController, self).setUp()
        self.db = unit_test_utils.FakeDB()
        self.store = unit_test_utils.FakeStoreAPI()
        self.policy = unit_test_utils.FakePolicyEnforcer()
        self.notifier = unit_test_utils.FakeNotifier()
        self._create_images()
        self._create_image_members()
        self.controller = glance.api.v2.image_members\
                                       .ImageMembersController(self.db,
                                                               self.policy,
                                                               self.notifier,
                                                               self.store)
        glance.store.create_stores()

    def _create_images(self):
        self.db.reset()
        self.images = [
            _db_fixture(UUID1, owner=TENANT1, name='1', size=256,
                        is_public=True, location='%s/%s' % (BASE_URI, UUID1)),
            _db_fixture(UUID2, owner=TENANT1, name='2',
                        size=512, is_public=True),
            _db_fixture(UUID3, owner=TENANT3, name='3',
                        size=512, is_public=True),
            _db_fixture(UUID4, owner=TENANT4, name='4', size=1024),
        ]
        [self.db.image_create(None, image) for image in self.images]

        self.db.image_tag_set_all(None, UUID1, ['ping', 'pong'])

    def _create_image_members(self):
        self.image_members = [
            _db_image_member_fixture(UUID1, TENANT2),
            _db_image_member_fixture(UUID1, TENANT3),
            _db_image_member_fixture(UUID3, TENANT4),
            _db_image_member_fixture(UUID3, TENANT2),
            _db_image_member_fixture(UUID4, TENANT1),
        ]
        [self.db.image_member_create(None, image_member)
            for image_member in self.image_members]

    def test_index(self):
        request = unit_test_utils.get_fake_request()
        output = self.controller.index(request, UUID1)
        self.assertEqual(2, len(output['members']))
        actual = set([image_member['member_id']
                      for image_member in output['members']])
        expected = set([TENANT2, TENANT3])
        self.assertEqual(actual, expected)

    def test_index_no_members(self):
        request = unit_test_utils.get_fake_request()
        output = self.controller.index(request, UUID2)
        self.assertEqual(0, len(output['members']))
        self.assertEqual({'members': []}, output)

    def test_index_private_image(self):
        request = unit_test_utils.get_fake_request(tenant=TENANT2)
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.index,
                          request, UUID4)

    def test_index_private_image_visible_members_admin(self):
        request = unit_test_utils.get_fake_request(is_admin=True)
        output = self.controller.index(request, UUID4)
        self.assertEqual(1, len(output['members']))
        actual = set([image_member['member_id']
                      for image_member in output['members']])
        expected = set([TENANT1])
        self.assertEqual(actual, expected)

    def test_create(self):
        request = unit_test_utils.get_fake_request()
        image_id = UUID2
        member_id = TENANT3
        output = self.controller.create(request, image_id=image_id,
                                        member_id=member_id)
        self.assertEqual(UUID2, output['image_id'])
        self.assertEqual(TENANT3, output['member_id'])

    def test_create_private_image(self):
        request = unit_test_utils.get_fake_request(tenant=TENANT2)
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.create,
                          request, image_id=UUID4, member_id=TENANT2)

    def test_create_image_does_not_exist(self):
        request = unit_test_utils.get_fake_request()
        image_id = 'fake-image-id'
        member_id = TENANT3
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.create,
                          request, image_id=image_id, member_id=member_id)

    def test_delete(self):
        request = unit_test_utils.get_fake_request()
        member_id = TENANT2
        image_id = UUID1
        res = self.controller.delete(request, image_id, member_id)
        self.assertEqual(res.body, '')
        found_member = self.db.image_member_find(image_id, member_id)
        self.assertEqual(found_member, [])

    def test_delete_private_image(self):
        request = unit_test_utils.get_fake_request(tenant=TENANT2)
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.delete,
                          request, UUID4, TENANT1)

    def test_delete_image_does_not_exist(self):
        request = unit_test_utils.get_fake_request()
        member_id = TENANT2
        image_id = 'fake-image-id'
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.delete,
                          request, image_id, member_id)

    def test_delete_member_does_not_exist(self):
        request = unit_test_utils.get_fake_request()
        member_id = 'fake-member-id'
        image_id = UUID1
        found_member = self.db.image_member_find(request.context,
                                                 image_id=image_id,
                                                 member=member_id)
        self.assertEqual(found_member, [])
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.delete,
                          request, image_id, member_id)

    def test_shared_image_index(self):
        request = unit_test_utils.get_fake_request()
        images = self.controller.index_shared_images(request, TENANT2)
        expected_images = {'shared_images': [{'image_id': UUID1},
                                             {'image_id': UUID3}]}
        self.assertEquals(images, expected_images)

    def test_shared_image_index_member_not_found(self):
        request = unit_test_utils.get_fake_request()
        member_id = 'fake-member'
        images = self.controller.index_shared_images(request, member_id)
        expected_images = {'shared_images': []}
        self.assertEquals(images, expected_images)
