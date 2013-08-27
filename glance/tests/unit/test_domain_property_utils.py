# Copyright 2012 OpenStack Foundation.
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

import os
import shutil

import fixtures

from glance.common import property_utils
from glance.tests import utils

class TestPropertyRules(utils.BaseTestCase):

    def setUp(self):
        super(TestPropertyRules, self).setUp()
    #    self.test_dir = self.useFixture(fixtures.TempDir()).path
    #    self.prop_file = os.path.join(self.test_dir, 'property-protections.conf')
    #    self.config(property_protection_file=self.prop_file)

    #def set_property_protections(self, rules=None):
    #    if rules is None:
    #        self._copy_data_file('property-protections.conf', self.test_dir)
    #    else:
    #        fap = open(CONF.property_protection_file, 'w')
    #        fap.write(rules)
    #        fap.close()

    #def _copy_data_file(self, file_name, dst_dir):
    #    src_file_name = os.path.join('glance/tests/etc', file_name)
    #    shutil.copy(src_file_name, dst_dir)

    def test_check_property_rules_read_permitted_admin_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules('test_prop',
                        'read', ['admin']))

    def test_check_property_rules_read_permitted_specific_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules(
                        'owner_specified_prop', 'read', ['member']))

    def test_check_property_rules_read_unpermitted_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertFalse(self.rules_checker.check_property_rules('test_prop',
                        'read', ['test_role]']))

    def test_check_property_rules_create_permitted_admin_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules('test_prop',
                        'create', ['admin']))

    def test_check_property_rules_create_permitted_specific_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules(
                        'owner_specified_prop', 'create', ['member']))

    def test_check_property_rules_create_unpermitted_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertFalse(self.rules_checker.check_property_rules('test_prop',
                        'create', ['test_role']))

    def test_check_property_rules_update_permitted_admin_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules('test_prop',
                        'update', ['admin']))

    def test_check_property_rules_update_permitted_specific_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules(
                        'owner_specified_prop', 'update', ['member']))

    def test_check_property_rules_update_unpermitted_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertFalse(self.rules_checker.check_property_rules('test_prop',
                        'update', ['test_role']))

    def test_check_property_rules_delete_permitted_admin_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules('test_prop',
                        'delete', ['admin']))

    def test_check_property_rules_delete_permitted_specific_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertTrue(self.rules_checker.check_property_rules(
                        'owner_specified_prop', 'delete', ['member']))

    def test_check_property_rules_delete_unpermitted_role(self):
        self.rules_checker = property_utils.PropertyRules()
        self.assertFalse(self.rules_checker.check_property_rules('test_prop',
                        'delete', ['test_role']))
